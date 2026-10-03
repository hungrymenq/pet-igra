"""Проверить скачанные ресурсы по контрольным суммам; файлы не изменяются."""
from pathlib import Path, PureWindowsPath
import hashlib
import json
import re
import sys
import wave


def проверить():
    корень = Path(__file__).resolve().parent
    манифест = json.loads((корень / 'Проверка для админа/Контрольные суммы.json').read_text('utf8'))
    строки = манифест['файлы']
    if len(строки) != манифест['ресурсов']:
        raise ValueError('Не совпадает число файлов в манифесте.')
    ожидаемые = set()
    for строка in строки:
        файл = (корень / строка['путь']).resolve()
        if not файл.is_relative_to(корень):
            raise ValueError('Путь выходит за пределы репозитория.')
        if файл in ожидаемые:
            raise ValueError('Повторяется ресурс: ' + строка['путь'])
        ожидаемые.add(файл)
        if not файл.is_file() or файл.stat().st_size != строка['байт']:
            raise ValueError('Не найден файл или изменён размер: ' + строка['путь'])
        хеш = hashlib.sha256()
        with файл.open('rb') as поток:
            for блок in iter(lambda: поток.read(1024 * 1024), b''):
                хеш.update(блок)
        if хеш.hexdigest() != строка['sha256']:
            raise ValueError('Изменено содержимое: ' + строка['путь'])
        if файл.suffix.lower() == '.wav':
            with wave.open(str(файл), 'rb') as звук:
                if (звук.getnchannels(), звук.getsampwidth(), звук.getframerate()) != (1, 2, 44100) or звук.getnframes() == 0:
                    raise ValueError('Неверный формат WAV: ' + строка['путь'])
    for вариант in {строка['вариант'] for строка in строки}:
        папка = корень / вариант
        фактические = {файл.resolve() for архив in ('models.pck.files', 'sfx.pck.files') for файл in (папка / архив).rglob('*') if файл.is_file()}
        нужные = {файл for файл in ожидаемые if файл.is_relative_to(папка)}
        if фактические != нужные:
            raise ValueError('Лишние или отсутствующие ресурсы: ' + вариант)
        for ecm in (папка / 'models.pck.files').rglob('*.ecm'):
            текст = ecm.read_bytes().decode('gb18030')
            события = re.findall(r'EventType: 101\r*\n.*?(?=EventType:|CombineActName:|ScriptCount:|$)', текст, re.S)
            for событие in события:
                for путь in re.findall(r'^FxFilePath: ([^\r\n]+)', событие, re.M):
                    if 'jeff_fw' not in путь.lower():
                        continue
                    ссылка = PureWindowsPath(путь)
                    if ссылка.is_absolute() or ссылка.drive or '..' in ссылка.parts:
                        raise ValueError('Небезопасный путь звука.')
                    wav = папка.joinpath('sfx.pck.files', *ссылка.parts)
                    if wav.resolve() not in нужные:
                        raise ValueError('Звук отсутствует в проверенном составе: ' + путь)
        print('Проверен комплект: ' + вариант)
    print('Готово: проверены ' + str(len(ожидаемые)) + ' ресурсов. Файлы не изменялись.')


if __name__ == '__main__':
    try:
        проверить()
    except Exception as ошибка:
        print('Ошибка проверки: ' + str(ошибка), file=sys.stderr)
        sys.exit(1)
