from ast import arg
import difflib
import hashlib
import hashtag
import hmac
import json
import random
import re
import string

import app
from local_constants import *

from datetime import datetime


def generate_id() -> str:
    digits = string.digits

    while True:
        first, second = [], []

        for _ in range(4):
            first.append(digits[random.randint(0, len(digits)-1)])
            second.append(digits[random.randint(0, len(digits)-1)])

        first = ''.join(first)
        second = ''.join(second)

        id = '.'.join([first, second])
        ad_query = app.Ad.query.filter_by(id=id).all()

        if not ad_query:
            break

    return id


def validate_request(request_data, token: str, trusted_users: list) -> bool:
    if request_data.is_json:
        requesting_user = request_data.json['id']

        if requesting_user in trusted_users:
            auth_data = request_data.json.copy()
            remove_keys = ['target_user', 'is_admin', 'status']

            for key in remove_keys:
                if key in auth_data.keys():
                    del auth_data[key]

            authentication = authenticate(auth_data, token, trusted_users)

            if authentication['status'] == 'success':
                
                return True

        return False

    return False


def repack_data(data: dict) -> dict:
    repack = {
        'id'        : data.get('id', None),
        'first_name': data.get('first_name', None),
        'last_name' : data.get('last_name', None),
        'username'  : data.get('username', None),
        'photo_url' : data.get('photo_url', None),
        'auth_date' : data.get('auth_date', None),
        'hash'      : data.get('hash', None)
    }

    return repack


def authenticate(auth_data: dict, token: str) -> dict:
    status = {
        'status'    : '',
        'id'        : None,
        'username'  : None,
        'first_name': None,
        'last_name' : None,
        'photo_url' : None,
        'auth_date' : None,
        'hash'      : 'success'
    }

    if auth_data['id'] == None:
        status['status'] = 'ID inválida. Por favor, faça o login novamente.'

        return status

    if auth_data['username'] == None:
        status['status'] = 'Por favor, crie um nome de usuário antes de utilizar este site.'

        return status

    user_query = app.User.query.filter_by(id=auth_data['id']).first()

    if user_query:
        block = user_query.blocked_until

        if not block < datetime.now():
            status['status'] = f'Você só poderá enviar uma nova mensagem após {block.strftime("%d/%m às %H:%Mh")}.'

            return status

        if user_query.is_banned:
            status['status'] = f'Este usuário foi banido do Bazar BGB e, por isso, não poderá enviar mensagens.'

            return status['status']

    day_auth_time = 86_400
    auth_hash = auth_data['hash']
    auth_data.pop('hash', None)

    data_check_string = []

    for key in sorted(auth_data.keys()):
        if auth_data[key] != None:
            data_check_string.append(key + '=' + str(auth_data[key]))

    data_check_string = '\n'.join(data_check_string)

    token_secret_key = hashlib.sha256(token.encode()).digest()
    hmac_hash = hmac.new(token_secret_key, msg=data_check_string.encode(), digestmod=hashlib.sha256).hexdigest()

    auth_date = datetime.fromtimestamp(int(auth_data['auth_date']))
    now = datetime.now()

    auth_delta = now - auth_date

    if hmac_hash != auth_hash:
        status['status'] = 'Falha de autenticação [HA]. Por favor, faça o login novamente.'

    elif auth_delta.seconds > day_auth_time:
        status['status'] = 'Falha de autenticação [TI]. Por favor, faça o login novamente.'

    else:
        userid = int(auth_data['id'])

        status['status']     = 'success'
        status['id']         = userid
        status['username']   = auth_data['username']
        status['first_name'] = auth_data['first_name']
        status['last_name']  = auth_data['last_name']
        status['hash']       = auth_hash
        status['auth_date']  = auth_data['auth_date']
        status['photo_url']  = auth_data['photo_url']

    return status


def manage_index(index: int) -> str:
    if index < 10:
        index = f'0{index}'

    return index


def unpack_json(data: dict) -> None:
    print('*' * 25)
    
    for key in data.keys():
        if isinstance(data[key], dict):
            unpack_json(data[key])
        
        print(f'{key}: {data[key]}')
    
    print('*' * 25)


def group_ads(ads: dict) -> str:
    groups = {
        'Apenas Venda'   : [],
        'Apenas Troca'   : [],
        'Venda ou Troca' : [],
        'Leilão Externo' : [],
        'Procura'        : [],
    }
    message = ''

    for item in ads:
        item_type = item['type']
        groups[item_type].append(item)

    mapping = {
        'Apenas Venda'   : '💵 #VENDO',
        'Apenas Troca'   : '🤝 #TROCO',
        'Venda ou Troca' : '⚖️ #VENDO OU #TROCO',
        'Leilão Externo' : '🔨 #LEILÃO',
        'Procura'        : '🔎 #PROCURO'
    }

    index = 1

    for group in groups.keys():
        if len(groups[group]) > 0:
            item_list = groups[group]
            message += f'{mapping[group]}\n\n'

            for item in item_list:
                name_tag = hashtag.generate_tag(item['name'])
                message += f'\t\t➤ #{manage_index(index)} {name_tag}'
                index += 1

                if item["type"] == "Apenas Venda" or item["type"] == "Venda ou Troca":
                    message += f' R$ {item["price"]}'

                if len(item['description']) > 0:
                    new_line = '\n'
                    message += f'{new_line}       {item["description"].replace(new_line, ". ")}'

                message += '\n'

            message += '\n'

    return message


def unpack_command_and_arguments(text: str) -> list:
    command, *arguments = text.split()
    return command, *arguments


def unpack_message_data(message_key: str, data: dict) -> list:
    message         = data[message_key]['reply_to_message']['text']
    message_id      = data[message_key]['reply_to_message']['forward_from_message_id']
    chat_message_id = data[message_key]['reply_to_message']['message_id']
    infos           = data[message_key]['reply_to_message']['text'].split('\n\n')
    user            = data[message_key]['from']['username']

    return message, message_id, chat_message_id, infos, user


def fix_target(text: str) -> str:
    if '#' not in text:
        return '#' + text + ' '
    return text


def format_price(text: str) -> str:
    text = text.replace('.', '')

    if ',' not in text:
        text = text + ',00'

    if '.' not in text and len(text) > 6:
        text = text[:-6] + '.' + text[-6:]

    return text


def rebuild_formatting(text: str) -> str:
    user_id_pattern = re.compile('\[[0-9]+\]')
    ad_header_pattern = re.compile('(Anúncio|Leilão) de @\w+')
    ad_id_pattern = re.compile('[0-9]{4}\.[0-9]{4}')

    user_id = re.search(user_id_pattern, text)
    ad_header = re.search(ad_header_pattern, text)
    ad_id = re.search(ad_id_pattern, text)

    text = re.sub(user_id_pattern, f'<code>{user_id.group()}</code>', text)
    text = re.sub(ad_header_pattern, f'<strong>{ad_header.group()}</strong>', text)
    text = re.sub(ad_id_pattern, f'<code>{ad_id.group()}</code>', text)

    return text   


def replace_last_comma(text: str) -> str:
    last_comma_index = text.rfind(',')
    text = text[:last_comma_index] + ' e' + text[last_comma_index + 1:].rstrip()

    return text


def remove_duplicates(list_to_clean: list) -> list:
    list_to_clean = list(set(list_to_clean))
    list_to_clean.sort()

    return list_to_clean


def assemble_response(command: str, arguments: list, user: str, items_found: list, items_not_found: list) -> str:
    response_complement = {
        '/r':  '<b>removeu</b>',
        '/n':  '<b>negociou</b>',
        '/v':  '<b>vendeu</b>',
        '/ap': '<b>alterou o preço</b>'
    }

    items_found = remove_duplicates(items_found)
    items_not_found = remove_duplicates(items_not_found)
    items_not_found = list(set(items_not_found) - set(items_found))
    items_not_found.sort()

    if len(items_found) > 0 and len(items_not_found) == 0:
        response = f'@{user} {response_complement[command]}'
        
        if len(items_found) == 1 and command != '/ap':
            response += f' o item {items_found[0].rstrip()}!'

        elif len(items_found) == 1 and command == '/ap':
            response += f' do item {items_found[0].rstrip()}!'
        
        else:
            response += f' os itens '
            response += f'{", ".join(items_found)}!'

        if len(items_found) > 1:
            response = replace_last_comma(response)

    elif len(items_found) > 0 and len(items_not_found) > 0:
        response = f'@{user} {response_complement[command]}'

        if len(items_found) == 1:
            response += f' o item {items_found[0].rstrip()}!'

        else:
            response += f' os itens {", ".join(items_found)}!'
            response = replace_last_comma(response)
        
        if len(items_not_found) == 1:
            response += f'\n\nMas o item {items_not_found[0].rstrip()} não foi encontrado!'

        else:
            response += f'\n\nMas os itens {", ".join(items_not_found)} não foram encontrados!'
            response = replace_last_comma(response)

    else:
        response = "Nenhum item foi encontrado!"

    return response


def handle_removal(message, command, arguments, items_found, items_not_found, strike_pattern):
    complement = {
        '/r': 'REMOVIDO',
        '/n': 'NEGOCIADO',
        '/v': 'VENDIDO',
    }
    pattern         = re.compile('(#[0-9]{2} #+.+)(\n*  .*[^\n\n])*')
    strike_pattern  = re.compile('×(.+)\n+\s+.+×')
    split_message   = message.split('  ➤ ')

    for split in split_message:
        if '×' not in split:
            match = re.match(pattern, split)
            
            if match:
                for argument in arguments:
                    argument = fix_target(argument)

                    if argument in match.group():
                        replacement = f'  ➤ ×<s>{match.group()}</s>× {complement[command]}'
                        message = message.replace(f'  ➤ {match.group()}', replacement)
                        split = split.replace(f'  ➤ {match.group()}', replacement)
                        items_found.append(argument.strip())
                    
                    else:
                        items_not_found.append(argument.strip())

        elif '×' in split:
            search = re.search(strike_pattern, split)
            
            if search:
                changed_item = re.sub(strike_pattern, f'×<s>{search.group()[1:-1]}</s>×', split)
                message = message.replace(split, changed_item)

    message = rebuild_formatting(message)

    return message, items_found, items_not_found


def handle_price_change(message, arguments, items_found, items_not_found, strike_pattern):
    price_pattern   = re.compile('([0-9]+.[0-9]{3},[0-9]{2})|([0-9]{3},[0-9]{2})')
    target          = arguments[0]
    new_price       = format_price(arguments[1])

    for split in message.split('  ➤ '):
        if '×' not in split and target in split:
            changed_item = re.sub(price_pattern, new_price, split)
            message = message.replace(split, changed_item)
            items_found.append(target)

        elif target not in split:
            items_not_found.append(target)

        elif '×' in split:
            search = re.search(strike_pattern, split)
            
            if search:
                changed_item = re.sub(strike_pattern, f'×<s>{search.group()[1:-1]}</s>×', split)
                message = message.replace(split, changed_item)

    message = rebuild_formatting(message)

    return message, items_found, items_not_found


def edit_ad(message_key: str, data: dict) -> str:
    print('EDITING AD')

    text = data[message_key]['text']
    response_message = ''
    command, *arguments = unpack_command_and_arguments(text)
    message, message_id, *unused_infos, user = unpack_message_data(message_key, data)
    strike_pattern  = re.compile('×(.+)\n+\s+.+×')
    items_found, items_not_found = [], []

    response = {
        'success': False,
    }

    if command in REMOVE_COMMANDS or command in PRICE_COMMANDS:
        if command in REMOVE_COMMANDS:
            new_message, items_found, items_not_found = handle_removal(message, command, arguments, items_found, items_not_found, strike_pattern)

        elif command in PRICE_COMMANDS:
            new_message, items_found, items_not_found = handle_price_change(message, arguments, items_found, items_not_found, strike_pattern)        

        response['success'] = True
        response['message_id'] = message_id
        response['text'] = new_message
    
    try:
        response_message = assemble_response(command, arguments, user, items_found, items_not_found)

    except Exception as error:
        print('ERROR at response message assemble: ', error)
    
    response['response'] = response_message
    print('TARGET: ', command, arguments)

    return response


def manage_auctions(data: dict, ending_date: str) -> str:
    message = f'Encerramento: {ending_date}\n\n'

    index = 1
    for item in data:
        name = hashtag.generate_tag(item['name'])

        if index == 1:
            message += f'➤ #{manage_index(index)} {name}\n'
        else:
            message += f'\n➤ #{manage_index(index)} {name}\n'

        message += f'Lance inicial: R$ {item["starting_price"]}\n'
        message += f'Incremento: R$ {item["increment"]}\n'
        message += f'Último lance: -'

        if len(item['description']) > 0:
            message += f'\nDetalhes: {item["description"]}'

        message += '\n\n'

        index += 1

    return message


def validate_bid(item: str, value: str, info: str, user: str):
    print('VALIDATING BID')
    info = info.lstrip()
    value_pattern = re.compile('[^0-9,-]')

    print('GETTING INFO')
    print(info)
    
    game            = info.split('\n')[0]
    ask_text        = info.split('\n')[1]
    increment_text  = info.split('\n')[2]
    last_bid_text   = info.split('\n')[3]

    ask         = float(ask_text.split(':')[-1].replace('R$', '').replace(',', '.'))
    increment   = float(increment_text.split(':')[-1].replace('R$', '').replace(',', '.'))
    last_bid    = re.sub(value_pattern, '', last_bid_text.split(':')[-1]).replace(',', '.')
    last_bid    = ask if '-' in last_bid else float(last_bid)
    value       = float(re.sub(value_pattern, '', value))

    if last_bid == ask or value >= last_bid and (value - last_bid) >= increment:
        text = f'R$ {format(float(value), ".2f").replace(".", ",")} por @{user}'

        if '-' in last_bid_text:
            new_bid = last_bid_text.replace('-', text)

        else:
            new_bid = f'Último lance: {text}'

        return {
            'success': True,
            'new_bid': new_bid,
            'last_bid_text': last_bid_text
        }

    return {
        'success': False,
        'error': 'Lance inválido. \n\nPor favor, verifique se o valor foi suficiente para superar o último lance válido com o incremento definido pelo leiloeiro.'
    }


def build_tracking_message(info: dict):
    print(info)
    message = '<strong>Últimos lances válidos</strong>\n\n'

    for key, value in zip(info.keys(), info.values()):
        message += f'{key}: {value}\n'

    return message


def tracking(message: str):
    print('TRACKING_CALLED')
    number_tag_pattern  = re.compile('#[0-9]{2}')
    username_pattern    = re.compile('@\w+')
    last_bid_pattern    = re.compile('R\$ [0-9]{2,5}?,[0-9]{2}')
    games               = message.split('\n\n')[2:-2]
    content             = {}

    for game in games:
        for row in game.split('\n'):
            if 'Jogo' in row:
                number_tag = re.search(number_tag_pattern, row)

                if number_tag:
                    content[number_tag.group()] = ''

            elif 'Último lance:' in row:
                username_match = re.search(username_pattern, row)
                last_bid_match = re.search(last_bid_pattern, row)

                username = username_match.group() if username_match else ''
                last_bid = last_bid_match.group() if last_bid_match else ''

                text = f'{last_bid} - {username}'
                content[number_tag.group()] = text

    return build_tracking_message(content)


def manage_bids(data: dict):
    print('MANAGE_BIDS_CALLED')
    status = {}
    bid = data['message']['text'].replace('R$', '').replace(',', '.')

    if bid.count('#') == 1 and len(bid.split()) == 2:
        message, message_id, chat_message_id, infos, user = unpack_message_data(data)
        item, value = bid.split()

        if item not in message:
            status = {
                'success': False,
                'error': 'Item não encontrado.\n\nPor favor, verifique na mensagem principal pelo identificador correto do item.'
            }

        for info in infos:
            if item in info:
                result = validate_bid(item, value, info, user)

                if result['success']:
                    id_pattern = re.compile('[0-9]{4}\.[0-9]{4}')
                    header_pattern = re.compile('^Leilão de @[\w]* \[[0-9]*\]')

                    new_info = info.replace(result['last_bid_text'], result['new_bid'])
                    new_message = message.replace(info, new_info)

                    id_match = re.search(id_pattern, new_message)
                    header_match = re.search(header_pattern, new_message)

                    if id_match and header_match:
                        new_message = new_message.replace(id_match.group(), f'<code>{id_match.group()}</code>')
                        new_message = new_message.replace(header_match.group(), f'<strong>{header_match.group()}</strong>')

                    tracking_message = tracking(new_message)

                    status =  {
                        'success': True,
                        'new_message': new_message,
                        'message_id': message_id,
                        'tracking_message': tracking_message,
                        'chat_message_id': chat_message_id
                    }

                else:
                    status = result

    elif bid.count('#') > 1:
        status = {
            'success': False,
            'error': 'Por favor, siga o formato\n\n#NÚMERO_DO_ITEM VALOR_DO_LANCE\n(Ex. #01 50)\n\ne informe apenas um único lance por mensagem.'
        }

    return status


def auction_time_validation(data: dict) -> bool:
    pass


def assemble_message(data: dict) -> str:
    message = ''

    if data['type'] == 'standard':
        ads = group_ads(data['boardgames'])
        message += '<strong>Anúncio de '
        
    else:
        ads = manage_auctions(data['auctions'], data['ending_date'])
        message += '<strong>Leilão de '

    message += f'@{data["username"]}</strong> [<code>{data["id"]}</code>]\n\n'
    message += ads

    if len(data['general_description']) > 0:
        message += data['general_description'] + '\n\n'

    message += f'📌 #{data["city"].replace(" ", "").replace("-", "")} #{data["state"]}'

    return message


def calculate_similarity(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, a, b).ratio()


def has_same_message(message: str):
    for ad in app.Ad.query.order_by(app.Ad.id).all():
        similarity = calculate_similarity(json.dumps(message), json.dumps(ad.content))

        if similarity == 1:
            return ad.id

    return None


def get_ad_owner(message: str) -> str:
    pattern = re.compile('@[\w]+\s\[[0-9]+\]')
    search = username_and_id = re.search(pattern, message)

    if search:
        username_and_id = search.group(0)
        username = username_and_id.split(' ')[0].replace('@', '')
        id = int(username_and_id.split(' ')[1][1:-1])

        return id, username

    return None, None
