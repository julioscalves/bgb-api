import re


def remove_special_chars(string):
    targets = [
        '?', '"', "'", '!', '¡', ',', 'ª',
        '.', '‘', '¿', '{', '[', '}', ']',
        '_', '#', '½', '+', '*', '%', 'º',
        '°', ')', 'ª',
        'Miniatures Game',
    ]

    for target in targets:
        string = string.replace(target, '')

    return string


def merge_hyphens(string):
    index = string.find('-')

    try:
        if index > 0:
            if string[index-1] != ' ' and string[index+1] != ' ':
                string = string.replace('-', '')

    except IndexError:
        pass

    return string


def replace_special_chars(string):
    mapping = {
        'ö': 'o', 'à': 'a', 'ū': 'u', '&': 'N',
        '$': 's', ' –': ':', '–': ':', '(': ':',
        'The Roleplaying Game'  : 'RPG',
        'Roleplaying Game'      : 'RPG',
        'Role Playing Game'     : 'RPG',
        'X-Wing'                : 'XWing',
        'Y-Wing'                : 'YWing',
        'U-Wing'                : 'UWing',
        'Set #'                 : 'Set',
        '40,000'                : '40k',
        '40.000'                : '40k',
        '40000'                 : '40k',
        '₂'                     : '2'
    }

    for special, letter in mapping.items():
        string = string.replace(special, letter)

    return string


def manage_series(string):
    series = {
        'Pandemic',             'Dungeons & Dragons',   'Zombicide',            'Zpocalypse',
        'Zooloretto',           'Wings of Glory',       'World of Darkness',    'Black Plague',
        'Green Horde',          'Zombie Dice',          'The Boardgame',        'Zombie Fluxx',
        'DC Comics',            'Marvel',               'GURPS',                'Star Wars',
        'O Senhor dos Anéis',   'A Guerra dos Tronos',  'Guerra dos Tronos',    'Tiny Epic',
        'Invader',              'Dark Side',            'Bang',                 'Encantados',
        'Exploding Kittens',    'Ticket to Ride',       'Clank',                '7 Wonders',
        'Fronteira do Império', 'Lenda dos Cinco Anéis','Viticulture',          'El Grande',
        'Pathfinder',           'Tormenta',             'T.I.M.E.',             'Advanced Dungeons & Dragons',
        'Achtung',              'Kick-Ass',             'CO2'                   'Dungeon World',
        'Chamado de Cthulhu',   'Tiny Dungeon',         'Ubongo',               'Warhammer 40k',
        'Carcassonne',          'Alhambra',             'Alien vs Predator',    'Card Kingdoms',
        'The Lord of the Rings','Core Rulebook',        'Bounty Hunters',       'Warhammer',
        'Triumph of Chaos',     'Pokémon',              'Digimon',              'Torg Eternity',
        'Munchkin',             'The Witcher',          'Viticulture: Tuscany', 'The Witcher: Old World',
        'Star Wars: Destiny',	'Anachrony',      		'Patchwork',            'BANG',
        'X-Wing',               'Y-Wing',               'A Máscara',            'Harry Potter',
        'Dwar7s',               'Marco Polo',           'Glen More',            'Disney',
        'Banco Imobiliário',    'Hanabi',               'Código Secreto',       'Codenames',
        'Pixel Tactics',        'Adventure Time',       'Men of Iron',          'Deckscape',
        'Kingdomino',           'Queendomino',          'Starcraft',            'Mass Effect',
        'Splendor',             'Monopoly',             'Arkham Horror',        'Scotland Yard',
        'Imagem & Ação',        'Resident Evil',        'DC',                   'Concordia',
        'Zurvivors'             'Codinomes',            'Código secreto',       'Black Stories',
        'Expansion',
    }

    for serie in series:
        match = re.match(f'{serie}[\s][^:]', string)
        search = re.search(f'{serie}[\s][^:]', string)

        if match or search:
            string = string.replace(serie, f'{serie}: ')

    return string


def split_into_tags(string):
    markers = [
        ':', '/', '\\', '–', '-', '—', '-'
    ]

    string = string.replace(' ', '')

    for marker in markers:
        string = string.replace(marker, ' #')

    string = '#' + string

    return string


def remove_numeric_tags(string):
    pattern = re.compile('(^#[\d]+\s+|#[\d]+$)+')
    search = re.search(pattern, string)

    if search:
        replacement = search.group().replace('#', '')
        string = re.sub(pattern, replacement, string)

    return string


def remove_single_tags(string):
    pattern = re.compile('\s#\s')
    search = re.search(pattern, string)

    if search:
        string = re.sub(pattern, ' ', string)

    return string


def push_roman_numbers(string):
    pattern = re.compile("([XVI]{1, 2})[XVI]+")
    search = re.search(pattern, string)

    if search:
        replacement = ' ' + search.group()
        string = re.sub(pattern, replacement, string)

    return string


def map_exceptions(string):
    mapping = {
        '#AMarvel #DeckBuildingGame': '#AMarvelDeckBuildingGame #Marvel',
        '#ManoplaDoInfinito #UmJogoLoveLetter': '#ManoplaDoInfinito Um Jogo #LoveLetter',
        '#Mission #RedPlanet': '#MissionRedPlanet',
    }

    for key in mapping.keys():
        if key in string:
            string = string.replace(key, mapping[key])

    return string


def generate_tag(string):
    tag = remove_special_chars(string)
    tag = manage_series(tag)
    tag = replace_special_chars(tag)
    tag = merge_hyphens(tag)
    tag = split_into_tags(tag)
    tag = remove_numeric_tags(tag)
    tag = remove_single_tags(tag)
    tag = push_roman_numbers(tag)
    tag = map_exceptions(tag)

    return tag
