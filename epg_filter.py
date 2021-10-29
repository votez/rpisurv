import xml.etree.ElementTree as ET
from datetime import datetime
import sys

visible_channels = ['inter', 'inter-plus-ua', '1-plus-1', '5kanal-ukraina', 'pervyj', 'moya-planeta',
                    'national-geographic', 'usadba', 'animal-planet', 'rt-doc', 'rossija-k', 'domashnij', 'ntv-mir',
                    'dozhd', 'kanal-nash', 'travel-adventure', 'nat-geo-wild', 'viasat-nature',
                    'zhivaya-planeta', 'teleputeshestvija', 'travel-channel', 'morskoj', 'history', 'viasat-history',
                    'istorija', 'TNT', 'tnt-4', 'CTC', 'tv-3', '4e', 'tvc', '5kanal', 'krasnaja-linija',
                    '8-kanal', '9-kanal', 'otp', 'mir', 'mir-24', 'sarafan', 'kvn-tv', 'piatnica', 'super',
                    'podmoskovje', 'yu-tv', 'vremya', 'rtvi', 'kinohit', 'kinomix', 'kinosemja', 'kinosvidanije',
                    'mnogo-tv', 'kinopokaz', 'tv1000', 'tv1000-action', 'tv1000-ru-kino', 'tv1000-world-kino', 'cinema',
                    'kino-tv', 'evrokino', 'muzhskoe-kino', 'hct', 'russkaja-comedija',
                    'kinokomedia', 'amedia-premium', 'amedia-hit', 'amedia-1', 'amedia-2', 'amc', 'fox', 'fox-life',
                    'paramount-channel', 'paramount-comedy', 'set', 'sony-sci-fi', 'sony-turbo', 'tv-xxi', 'mosfilm',
                    'lubimoe-kino', 'rodnoje_kino', 'pobeda', 'nashe-novoe-kino', 'russkij-bestseller', 'dom-kino',
                    'russkij-roman', 'russkij-detektiv', 'russkij-iluzion', 'iluzion-plus', 'feniks-plus-kino',
                    'mir-seriala', 'ntv-hit', 'ntv-serial', 'nostalgia', 'retro', 'indija-tv', 'zee-tv', 'discovery',
                    'discovery-science', 'dtx', 'id-xtra', 'tlc', 'viasat-explorer', 'rtg-tv', 'ocean-tv',
                    'zoopark', 'nauka-20', 't24', 'da-vinci-learning', '365-dnej', 'kto-est-kto', 'teatr-tv',
                    'zdorovoe-tv', 'voprosy-otvety', 'zhivi', 'mama', 'domashnije-zhivotnye', '1nezalegny-ua']
if __name__ == '__main__':
    today = datetime.today().strftime("%Y%m%d")

    tree = ET.parse(sys.stdin)
    newTree = ET.Element("tv")
    newTree.set('generator-info-name', 'cbilling.tv EPG')
    root = tree.getroot()
    channels = tree.findall('/channel')
    for element in channels:
        if element.get('id') in visible_channels:
            newTree.append(element)

    count = {}
    programs = tree.findall('/programme')
    for program in programs:
        channel = program.get('channel')
        curr = count.get(channel, 0)
        if channel in visible_channels and program.get('start').startswith(today):
            count[channel] = curr + 1
            newTree.append(program)

    ET.ElementTree(newTree).write(sys.stdout.buffer, encoding='UTF-8')
