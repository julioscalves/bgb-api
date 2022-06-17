import os
import re
import requests
import utils

from datetime import datetime, timedelta
from dotenv import load_dotenv
from flask import Flask, redirect, jsonify
from flask.globals import request
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy

from local_constants import *


env_path = os.path.join(os.getcwd(), '.env')

if os.path.exists(env_path):
    load_dotenv(env_path)

app = Flask(__name__)
CORS(app)

app.config['CORS_HEADERS'] = 'Content-Type'
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_NAME}.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

from schema import Ad, User


def notify(json_object: dict) -> dict:
    try: 
        message_id              = json_object['message']['reply_to_message']['message_id']
        reply_message_id        = json_object['message']['message_id']
        target_chat             = json_object['message']['reply_to_message']['chat']['id']
        sender                  = json_object['message']['from']['username']
        is_bot                  = json_object['message']['from']['is_bot']
        message_replied         = json_object['message']['reply_to_message']['text']
        target_chat_name        = json_object['message']['reply_to_message']['sender_chat']['title']
        target_id, target_user  = utils.get_ad_owner(message_replied)

        if (target_id != None and target_user != None) and (sender != target_user and is_bot == False):                  
            message_url = f'https://t.me/c/{int(str(target_chat).replace("-100", ""))}/{int(reply_message_id)}?thread={int(message_id)}'
            message = f'Seu anúncio no {str(target_chat_name)} recebeu uma nova mensagem de <strong>@{sender}</strong>!'

            reply_markup = {
                'inline_keyboard': [[
                    {
                        'text': '👉 Visualizar mensagem', 
                        'url': message_url
                    }
                ]]
            }

            payload = {
                'chat_id': target_id, 
                'text': message,
                'parse_mode': 'HTML',
                'disable_web_page_preview': True, 
                'reply_markup': reply_markup
            }

            post = requests.post(SUBMIT_URL, json=payload)
            utils.unpack_json(post.json())

            return jsonify({
                'status': post.status_code
            })

        return jsonify({
            'status': 'Nome/ID de usuário não encontrados [UINF].'
        })

    except Exception as e:
        error = str(e)
        print(error)
        return jsonify({
            'status': error
        })


def send_message(data: dict):
    default_parameters = {
        'disable_web_page_preview': True,
        'parse_mode': 'HTML',
    }

    payload = {**default_parameters, **data}
    response_message = requests.post(SUBMIT_URL, data=payload)

    return utils.unpack_json(response_message.json())


def ban(user_query: str) -> dict:
    user_query.is_banned = True
    db.session.commit()

    return jsonify({
        'status': 'success'
    })


def unban(user_query: str) -> dict:
    user_query.is_banned = False
    db.session.commit()

    return jsonify({
        'status': 'success'
    })


def reset(user_query: str) -> dict:
    yesterday = datetime.now() - timedelta(days=1)
    user_query.blocked_until = yesterday
    db.session.commit()

    return jsonify({
        'status': 'success'
    })


def block(user_query: str, arguments: list) -> dict:
    block = datetime.now() + timedelta(days=int(arguments[-1])) - timedelta(hours=3)
    user_query.blocked_until = block
    db.session.commit()

    return jsonify({
        'status': 'success'
    })


def get_user(user_query: str, user_id: int) -> dict:
    print('*' * 25)
    print('GET_USER', user_query)
    print('*' * 25)

    is_banned = "SIM" if user_query.is_banned == True else "NÃO"
    message = (
        f'Informações sobre o usuário {user_query.username}\n\n'
        f'Usuário: <strong>{user_query.username}</strong> [<code>{user_query.id}</code>]\n'
        f'Banido: {is_banned}\n'
        f'Último bloqueio por mensagem: até {user_query.blocked_until}'
    )

    data = {
        'chat_id': user_id,
        'text': message,
    }
    send_message(data)

    return jsonify({
        'status': 'success'
    })


def get_last_users_list(user_id: int) -> dict:
    users_query = User.query.order_by(User.blocked_until.desc()).limit(USER_LIST_SIZE)
    message = ''

    print('*' * 25)
    print('USER_LIST', users_query)
    print('*' * 25)

    if users_query:
        message += 'Lista dos usuários mais recentes do Bazar BGB\n\n'

        for query in users_query:
            is_banned = "SIM" if query.is_banned == True else "NÃO"
            message += (
                f'Usuário: <strong>{query.username}</strong> <code>[{query.id}]</code>\n'
                f'Banido: {is_banned}\n'
                f'Último bloqueio por mensagem: até {query.blocked_until}'
            )
            message += '\n\n'

    else:
        message = 'Lista de usuários vazia!'

    data = {
        'chat_id': user_id,
        'text': message,
    }
    send_message(data)

    return jsonify({
        'status': 'success'
    })


def format_reputation(amount: str) -> str:
    return "negociações" if int(amount) != 1 else "negociação"


def reputation(target: str, user_id: str) -> dict:
    message = ''
    gid = 2039765451
    sheet_id = '1qMWvLHqSCPFQnWAagpHYAAhCTfFjJzu5oQKHIaOW2oo'
    url = f'https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}'
    data = requests.get(url).text.encode('ISO-8859-1').decode()

    for line in data.split('\n')[1:]:
        row = line.strip().split(',')

        if row[0] == target:
            message = (
                f'<strong>Reputação de {target}</strong>\n'
                f'\n<code>Comprador: {row[1]:5}|{row[2]:>3} {format_reputation(row[2])}'
                f'\nVendedor:  {row[3]:5}|{row[4]:>3} {format_reputation(row[4])}'
                f'\nEm Trocas: {row[5]:5}|{row[6]:>3} {format_reputation(row[6])}'
                f'\n\nGeral:     {row[7]:5}|{row[8]:>3} {format_reputation(row[8])}</code>'
            )

    if len(message) == 0:
        message = 'Usuário sem reputação.'

    data = {
        'chat_id': user_id,
        'text': message,
    }
    send_message(data)

    return jsonify({
        'status': message
    })


@app.route('/submit_news', methods=['POST'])
def submit_news() -> dict:
    if request.method == 'POST' and request.is_json:
        data = request.get_json()

        return jsonify({
            'status': 'success'
        })
    
    return jsonify({
        'status': 'error'
    })


@app.route('/get_ad', methods=['GET', 'POST'])
def get_ad() -> dict:
    if request.is_json:
        ad_id = request.json['id']

        if '.' not in ad_id:
            ad_id = ad_id[:4] + '.' + ad_id[4:]

        ad_query = Ad.query.filter_by(id=ad_id).first()

        if ad_query:
            return jsonify(ad_query.content)

        return jsonify({
            'status': 'Anúncio não encontrado [NE]'
        })

    return jsonify({
        'status': 'Requisição inválida [NJ].'
    })


@app.route('/submit', methods=['GET', 'POST'])
def submit() -> dict:
    if request.is_json:
        print('*' * 25)
        print('SUBMIT', request.json)
        print('*' * 25)

        try:
            userid = request.json['id']
            username = request.json['username']
            user_query = User.query.filter_by(id=userid).first()

            print('*' * 25)
            print('SUBMIT_USER_QUERY', user_query)
            print('*' * 25)

            is_blocked = False if user_query == None else user_query.blocked_until > datetime.now()

            if is_blocked == False:
                future_date = datetime.now() + timedelta(days=DAYS_BLOCKED) - timedelta(hours=3)

                if user_query:
                    user_query.blocked_until = future_date                        

                else:
                    new_user = User(id=userid, username=username, is_banned=False, blocked_until=future_date)
                    db.session.add(new_user)

                message = utils.assemble_message(request.json)
                ad_type = request.json['type']

                if ad_type == 'standard':
                    json_content = request.json['boardgames']
                else:
                    json_content = request.json['auctions']

                same_message = utils.has_same_message(json_content)

                if same_message:
                    message += f'\n\nID: <code>{same_message}</code>'

                else:
                    ad_id = utils.generate_id()
                    new_ad = Ad(id=ad_id, content=json_content)
                    db.session.add(new_ad)
                
                    message += f'\n\nID: <code>{ad_id}</code>'

                db.session.commit()

                payload = {
                    'chat_id': BGB_BAZAR_CHANNEL_ID,
                    'text': message,
                    'parse_mode': 'HTML',
                    'disable_web_page_preview': True
                }
                post = requests.post(SUBMIT_URL, data=payload)
                utils.unpack_json(post.json())

                if (post.status_code != 200):
                    return jsonify({
                        'status': f'ERRO {post.status_code}.'
                    })

                return jsonify({
                    'status': 'success'
                })
        
        except Exception as e:
            exception = str(e)

            return jsonify({
                'status': f'ERROR: {exception}'
            })
        
        return jsonify({
                'status': 'Usuário impedido por tempo de envio [TI].'
            })

    return jsonify({
        'status': 'Requisição inválida [NJ/NA].'
    })


@app.route('/auth', methods=['GET', 'POST'])
def auth() -> dict:
    if request.is_json:
        repack = utils.repack_data(request.json)
        status = utils.authenticate(repack, TELEGRAM_TOKEN)

        return jsonify(status)

    return jsonify({
        'status': 'Requisição inválida [NJ].'
    })


@app.route('/updates', methods=['GET', 'POST'])
def router() -> dict:
    if request.is_json:
        try:
            utils.unpack_json(request.json)

            json_object = request.json
            response = {}
            auction_pattern = re.compile('Leilão de @[\w]+ \[[0-9]+\]')
            ad_pattern = re.compile('Anúncio de @[\w]+ \[[0-9]+\]')

            if 'reply_to_message' in json_object['message'] and json_object['message']['chat']['type'] != 'private':
                message_key = 'edited_message' if 'edited_message' in json_object.keys() else 'message'

                first_word = json_object[message_key]['text'].split(' ')[0]
                if first_word not in REMOVE_COMMANDS and first_word not in PRICE_COMMANDS:
                    response = notify(json_object)

                if auction_pattern.search(json_object[message_key]['reply_to_message']['text']):
                    if '#FINALIZADO' not in json_object['message']['text']:
                        data = utils.manage_bids(json_object)

                        if data['success'] == True:
                            update_message_data = {
                                'message_id': data['message_id'],
                                'chat_id': BGB_BAZAR_CHANNEL_ID,
                                'text': data['new_message'],
                            }
                            send_message(update_message_data)

                            tracking_message_data = {
                                'chat_id': BGB_BAZAR_COMMENTS_ID,
                                'text': data['tracking_message'],
                                'reply_to_message_id': data['chat_message_id'],
                            }
                            send_message(tracking_message_data)
                        
                        else:
                            error_message_data = {
                                'chat_id': BGB_BAZAR_COMMENTS_ID,
                                'text': data['error'],
                                'reply_to_message_id': json_object['message']['message_id'],
                            }
                            send_message(error_message_data)
                    
                    else:
                        auction_complete_data = {
                            'chat_id': BGB_BAZAR_COMMENTS_ID,
                            'text': 'Este leilão já foi finalizado.\n\nFique de olho nos próximos anúncios do Bazar!',
                            'reply_to_message_id': json_object['message']['message_id'],
                            'parse_mode': 'HTML',
                        }
                        send_message(auction_complete_data)                       

                elif ad_pattern.search(json_object[message_key]['reply_to_message']['text']):
                    owner_user_id_pattern = re.compile('\[[0-9]+\]')
                    owner_user_id = int(owner_user_id_pattern.search(json_object[message_key]['reply_to_message']['text']).group()[1:-1])

                    command_user_id = json_object[message_key]['from']['id']
                    is_bot_message = json_object[message_key]['from']['is_bot']

                    if (owner_user_id == command_user_id or command_user_id in TRUSTED_USERS) and is_bot_message == False:
                        text = json_object[message_key]['text']
                        command, *arguments = utils.unpack_command_and_arguments(text)
                        data = { 'success': False }

                        if command in utils.REMOVE_COMMANDS and len(arguments) >= 1:
                            data = utils.edit_ad(message_key, json_object)

                        elif command in utils.PRICE_COMMANDS and len(arguments) == 2:
                            data = utils.edit_ad(message_key, json_object)  

                        if data['success'] == True:
                            print(data)
                            update_ad_data = {
                                'message_id': data['message_id'],
                                'chat_id': BGB_BAZAR_CHANNEL_ID,
                                'text': data['text'],
                                'parse_mode': 'HTML',
                            }
                            send_message(update_ad_data)

                            response_message_data = {
                                'chat_id': BGB_BAZAR_COMMENTS_ID,
                                'text': data['response'],
                                'reply_to_message_id': json_object[message_key]['reply_to_message']['message_id'],
                            }
                            send_message(response_message_data)
                              
            elif 'Telegram' in json_object['message']['from']['first_name'] and BOT_NAME in json_object['message']['sender_chat']['username']:
                message_id = json_object['message']['message_id']
<<<<<<< HEAD
                message = ( 
                    'Ao finalizar uma negociação, utilize <a href="https://forms.gle/ijUTg5fZst4tgxx66">este formulário</a> de avaliação de reputação da outra parte.'
                    '\n\n'
                    'Quando precisar modificar algum item do seu anúncio, use os comandos listados <a href="https://t.me/bazarbgb/1165">nesta mensagem</a> conforme o respectivo caso.'
                    '\n\n'
                    'Bons negócios!'
=======
                message = (
                    'Ao finalizar uma negociação, utilize <a href="https://forms.gle/ijUTg5fZst4tgxx66">este formulário de avaliação</a> de reputação da outra parte.'
                    '\n\n'
                    'Quando precisar alterar a disponibilidade ou o valor de algum itens cadastrados, utilize os comandos listados <a href="https://t.me/bazarbgb/1165">nesta mensagem</a> conforme for o caso.'
>>>>>>> f563e5cc2271a67a0b81e8668bc54c1d06fc5535
                )
                
                message_key = 'edited_message' if 'edited_message' in json_object.keys() else 'message'
                
                if auction_pattern.search(json_object[message_key]['text']):
                    message += '\n\nPara dar um lance, siga o formato abaixo:\n\n #NUMERO_DO_JOGO LANCE\n\nQualquer mensagem fora deste formato será ignorada para fins de registro do lance.'

                message += '\n\nBons negócios!'

                reminder_data = {
                    'chat_id': BGB_BAZAR_COMMENTS_ID,
                    'text': message,
                    'disable_web_page_preview': True, 
                    'reply_to_message_id': message_id,
                    'parse_mode': 'HTML'
                }
                send_message(reminder_data)

            elif json_object['message']['entities'][0]['type'] == 'bot_command' and json_object['message']['chat']['type'] == 'private':
                user_id = json_object['message']['from']['id']
                text = json_object['message']['text']
                message = ''

                arguments = text.split(' ')

                if len(arguments) > 1:   
                    command, target = arguments[0], arguments[1]
                    target = target.replace('@', '')
                    is_target_not_admin = target not in TRUSTED_USERS and target not in TRUSTED_USERNAMES 

                    user_query = User.query.filter_by(username=target).first()  \
                                        if target.isdigit() == False            \
                                        else User.query.filter_by(id=target).first()

                    print('*' * 25)
                    print('USER_QUERY', user_query)
                    print('*' * 25)

                    if '/start' in command:
                        message = 'Bem-vindo ao bot oficial do Bazar BGB!'

                    if '/rep' in command:
                        target = f'@{target}'
                        response = reputation(target, user_id)

                    elif user_query:
                        if user_id in TRUSTED_USERS:
                            if '/reset' in command:
                                response = reset(user_query)
                                message = f'✅ Bloqueio do usuário {target} resetado!'
                            
                            elif '/user' in command:
                                response = get_user(user_query, user_id)

                            elif is_target_not_admin:
                                
                                if '/ban' in command:
                                    response = ban(user_query)
                                    message = f'✅ Usuário {target} banido!'

                                elif '/unban' in command:
                                    response = unban(user_query)
                                    message = f'✅ Usuário {target} desbanido!'

                                elif '/block':
                                    if len(arguments) != 3 and arguments[-1].isnumeric():
                                        message = f'❌ Este comando exige o formato /block id_de_usuário dias'

                                    else:
                                        response = block(user_query, arguments)
                                        message = f'✅ Usuário {target} bloqueado por {arguments[-1]} dias!'

                                else:
                                    message = f'❌ Comando inexistente!'
                                    response = jsonify({
                                        'status': 'Comando inexistente!'
                                    })
                            
                            else:
                                message = '❌ Admins não podem ter permissões limitadas!'
                                response = jsonify({
                                    'error': 'Comando inválido!'
                                })
                        
                        else:
                            message = '❌ Você não tem as permissões necessária para utilizar este comando!'
                            response = jsonify({
                                'error': 'Comando inválido!'
                            })

                    else:
                        message = '❌ Usuário não encontrado!'
                        response = jsonify({
                            'error': 'Comando inválido!'
                        })

                elif '/last_users' in text and user_id in TRUSTED_USERS:
                    response = get_last_users_list(user_id)
                
                else:
                    message = '❌ Comando inválido!'
                    response = jsonify({
                        'error': 'Comando inválido!'
                    })

                if len(message) > 0:
                    data = {
                        'chat_id': user_id,
                        'text': message,
                    }
                    send_message(data)

            else:
                message = '❌ Comando inválido!'
                data = {
                    'chat_id': json_object['message']['from']['id'],
                    'text': message,
                }
                send_message(data)
                response = jsonify({
                            'error': 'Comando inválido!'
                        })

            return response  

        except Exception as e:
            error = str(e)
            print('ERROR: ', error)
            return jsonify({
                'error': error
            })     

    return jsonify({
        'status': 'Requisição inválida [NJ].'
    })


@app.route('/')
def home() -> dict:
    return redirect('https://bgb.vercel.app/')


if __name__ == '__main__':
    app.run(debug=DEBUG_MODE)
