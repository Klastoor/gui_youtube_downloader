#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Данное «музыкальное» приложение исходя из введенных пользователем данных, 
производит поиск по общедоступным видео в YouTube, и предоставляет возможность 
скачать аудиодорожку из клипа в mp3 формате, со вставленной обложкой и 
корректной тегировкой: названий произведений и имен исполнителей из 
самых первых пяти соответствующих результатов запроса. 

- В основе графического интерфейса используется фреймворк «Tkinter» 
- В поисковых запросах а так же проверок корректности/работоспособности ссылок, 
отвечают такие модули как: «youtube_search», «BeautifulSoup4», «requests» 
- Скачивание осуществлено при помощи модуля: «youtube_dl» и встроенного в него модуля 
(для упаковки/переупаковки файлов): «FFmpeg» 
- Для многопоточного скачивания файлов используется библиотека «Thread»
- Работа с изображением происходит с помощью библиотеки «PIL»
- Вставка и редактирование тэгов в аудиофайлах используется библиотеке: «mutagen»

Приложение писалось для личного использования и в тоже время как основа - Beta версия
желаемого приложения.

Преследуемые цели которые удалось достичь:
- Возможность осуществлять поиск музыки и получать результат указав лишь: 
название трека/исполнителя/все сразу/некорректного ввода и тд
- Единовременно осуществлять n-ое количество скачек и в тоже время производить поиск
- Контролировать название файла, вдобавок автоматическое заполнение лишь основных аудио тэгов
- В обязательном порядке конечный аудиофайл должен быть с корректной обложкой

Цели в которых потерпел полное фиаско:
- формат аудиофайла должен быть Lossless в идеале что то вроде flac
минимальный порог формата с потерями это - aac, m4a
недопустимый формат - это mp3
Но в ходе написания кода выяснилось что лучший формат аудиодорожки может быть wav - что в целом
неплохо и можно как то работать и переупаковать в нужный формат, проставить нужные тэги худо-бедно, но реально.
Однако добавление обложки совсем иная задача и как это осуществить с любым другим форматом который не mp3,
я не знаю! Если же знаком такой способ, был бы очень признателен если расскажите о нем! А если еще с рабочем примером
то просто блеск!

- стиль написания кода, использование ооп для достижения максимальной результативности
прекрасно понимаю что мой код и мое использование классов источает боль, особенно в 
моменте функции «hook» где пришлось использовать костыль из за нехватки знаний как выполнить это с помощью классов
Буду премного благодарен если на примере моего «кода» покажите как его на самом деле следовало 
написать (хотя бы пару примеров) особенно в том моменте где при параллельном скачивание файлов
прогресс проставлялся именно в том месте где это нужно

в конечном итоге время затраченное с момента запуска скрипта до момента финального готового файла - очень большое..
"""

from os import path, getcwd
from tkinter import *
from tkinter import messagebox
from tkinter.ttk import Notebook
from tkinter.filedialog import asksaveasfilename
from youtube_search import YoutubeSearch as ys
import requests as req
from bs4 import BeautifulSoup as bf
from os import getcwd, path, remove
from youtube_dl import YoutubeDL
from mutagen.mp3 import MP3
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3, APIC
from threading import Thread
from PIL import Image
from loguru import logger

class Window:
    """ Основа всего приложения, создание родительского окна """

    def __init__(self, width, height, title="New window", icon=path.join(getcwd(), "youtube.ico"), resizable=(0, 0)):
        self.root = Tk()
        self.root.title(title)
        self.root.resizable(resizable[0], resizable[1])
        self.root.iconbitmap(icon)
        self.size_and_position(self.root, width, height)

        # добавление панели вкладок в главное окно
        self.tabs_control = Notebook(self.root, padding=(14,5))
        # Основная (стартовая) вкладка главного окна
        self.tab_1 = Frame(self.tabs_control)
        # Дополнительная (загрузочная) вкладка главного окна
        self.tab_2 = Frame(self.tabs_control)
        self.tabs_control.add(self.tab_1, text="MAIN")
        self.tabs_control.add(self.tab_2, text="DOWNLOADER")

        # Добавление клавиатурной навигации между вкладками
        self.tabs_control.enable_traversal()
        self.spis = dict()
        self.sk = 0

    def size_and_position(self, master, width=int(600), height=int(220)):
        """ Центрирование главного окна по центру экрана 
        
        master - главное окно
        width - ширина главного окна
        height - высота главного окна
.
        """

        # присваеваем переменным параметры экрана
        win_width, win_height = master.winfo_screenwidth(), master.winfo_screenheight()
        x = (win_width - width) // 2 
        y = (win_height - height) // 2
        master.geometry(f"{width}x{height}+{x}+{y}")

    def run(self):
        """ Запуск главного окна"""

        # Добавление в главное окно панель для "пагинации"
        self.tabs_control.grid(sticky=W+S+E+N)

        # Иницилизация основных компонентов работы с программой
        self.main_widget()
        self.root.mainloop()

    def paste(self, event):
        """ Вставка (после клика по правой кнопки мыши) в поисковую строку последние данные из буфера памяти """

        text_from_clipboard = self.root.clipboard_get()
        self.input_string.insert(0, text_from_clipboard)

    def clear(self):
        """ Очищает строку поиска 

            - self.input_string -> ""
            .
        """

        self.input_string.delete(0, END)

    def main_widget(self):
        """ Основные и постоянные виджеты программы """
        
        # Надпись над строкой поиска
        Label(self.tab_1, text="Download music from YouTube clip",fg="#df0a0a", font=('calibri', 26, 'bold')).grid(row=0, columnspan=2, pady=10)

        # Строка поиска
        self.input_string = Entry(self.tab_1, relief="solid", fg="#df0a0a", font=("Consolas", 16), width=40)
        self.input_string.focus()
        self.input_string.bind('<Return>', self.input_validate)
        self.input_string.bind('<Button-3>', self.paste)
        self.input_string.grid(row=2, column=0, columnspan=2, padx=5, sticky=E)

        # Кнопка очистить строку поиска
        Button(self.tab_1, text="❌", font=("Aria", 14) , border=0, borderwidth=0, command=self.clear, fg="#df0a0a").grid(row=2, column=2, padx=5, sticky=W)

        # Кнопка начать поиск
        search_button = Button(self.tab_1, text="Search", fg="white", bg="green", font = ("Aria", 17))
        search_button.bind("<Button-1>", self.input_validate)
        search_button.grid(row=3, columnspan=2, pady=25, sticky=S)

        # Отдельный фрейм для результирующих кнопок
        self.btn_group = Frame(self.root)
        self.btn_group.grid(row=4, rowspan=5, column=0, columnspan=4)

    def button_download(self, master, text, link, count):
        """ Непосредственно создание кнопки для скачивание аудиофайла
        
            master - Окно в котором будут создаватся окна
            text - Надпись на кнопке - название аудиофайла
            link - Ссылка на аудиофайл
            count - счетчик количества кнопок, от которого зависит в какой строке будет расположена кнопка
    ->
            command - вызов функции «сохранить как/куда» и передача ей название и ссылку
    ."""

        Button(master, text=text, bg="#df0a0a", fg="#dbd3d3", command=lambda: self.save_to_as(text, link) ).grid(row=count+4, pady=5, padx=5, sticky=N+S+W+E)


    def button_configure(self, check_list: list) -> object:
        """
        Функция получает список из словарей параметров, очищает родительский контейнер от прошлого запроса и  создав n колв.во кнопок с этими параметрами. Удаляет (если есть) существующие кнопки, добавляет ново созданные кнопки во фрейм :\n

            -   check_list = [ { name: str,  link: str }, ...  ]

                -    name - Название видео
                -    link - Ссылка на видео
        """
        # добавление счетчика для нумерации строк расположений кнопок скачивания
        count = 0
        if self.btn_group.winfo_children():
            # удаление виджетов из предидущего запроса
            [widg.destroy() for widg in self.btn_group.winfo_children()]

        for item in check_list:
            self.button_download(self.btn_group, item["name"], item["link"], count)
            count += 1
            logger.info(f"\nЭтап - 1) Кнопка для скачивания аудифайла №{count}, успешно создана!")
        self.size_and_position(self.root, height=int(f"{count*40+220}"))


    def save_to_as(self, name, href):
        """ Указать директорию сохранения mp3 файла и подкорректировать его название.
        После, запуск в отдельном потоке, скачивание файла

                name - название файла
                href - ссылка на указанный файл
            ."""
        # удаление точек в конце, если название попало под ограничение
        name = name[:-4] if name[-3:] == "..." else name[:]
        # запрос куда и с каким именем сохранять, предварительно заполнив дефолтн значения
        filepath = asksaveasfilename(
            initialdir = getcwd(), 
            title = "Сохранить новый файл как ...", 
            defaultextension = "mp3",
            filetype = [ ("mp3 аудиофайл", "*.mp3") ], 
            initialfile = name,
            )
        logger.info(f"\nЭтап - 2) Пользователь указал имя и место скачивания: \n{filepath=}\n")
        if filepath:

            self.tabs_control.select(self.tab_2)
            new_filename = filepath.split("/")[-1]
            new_filename = new_filename[:-4]
            new_filepath = "/".join(filepath.split("/")[:-1])

            # запуск скачивания в отдельном потоке
            Thread(target=self.download ,args=[new_filename, new_filepath, href]).start()
            logger.warning("\nЭтап - 3) Для скачивания был запущен отдельный поток")

    def download(self, title, path, link):
        """ 
        Скачивание и обработка mp3 аудиофайла где:

                title - Название файла
                path - Месторасположение файла
                link - Ссылка для скачивания
            .
        """
        # дефолтное располжение и название файла
        outtmpl = path + f'/{title}' + '.%(ext)s'
        ydl_opt = {
            'format': 'bestaudio/best',
            'outtmpl': outtmpl,
            'writethumbnail': 'embed_thumbnail',
            'progress_hooks': [self.my_hook],
            'postprocessors': [
                {
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192'
                },
            ],
        }

        with YoutubeDL(ydl_opt) as ydl:
            logger.success("\nЭтап - 4) Начало загрузки аудиофайла")
            ydl.extract_info(link)
            logger.warning("\nЭтап - 6) Файл успешно скачан, осталось добавить информацию в теги:")
            self.add_tags(path, title)
            logger.success(f"\nЭтап - 7) Песня {title} - готова к прослушиванию!")

    def my_hook(self, d: dict) -> object:
        """ Функция вызываемая событиями такими как: скачка объекта, его упаковка, тегирование и тд и тп;
        принимает и выводит значения о текущем этапе и состоянии объекта.
        Используемые параметры: 

        -    d["status"] - указывает на текущий этап
        -    d["filename"] - абсолютный путь и название файла
        -    d["_percent_str"] - величина (в %) уже 'пройденного пути'

        В конкретном Frame, на одной строке, создает два Label (в одном записано название файла, в другом прогресс выполнения)
        На основание добавления значений, в общий словарь где ключ - название файла, а содержание - позиция второго Label. Осуществляется сортировка
        """

        self.sk += 1
        if d['status'] == "downloading":
            string = d['filename'].split("\\")
            string = string[-1]
            string = string[:-4] + "mp3"
            procent = d['_percent_str']

            if  self.spis.get(string, False) != False:
                position_number = [self.spis[key] for key in self.spis.keys() if key == string] 
                position_number = int(position_number[0])
                all_child = self.tab_2.winfo_children()
                all_child[position_number].configure(text=procent)
                logger.info(f"\nЭтап - 5) Файл - {string} скачан на {procent}")

            else:
                # виджет отвечающий за название аудиофайла
                Label(self.tab_2, text=string, relief=SUNKEN, padx=25, pady=15).grid(row=len(self.spis), column=0, columnspan=2)
                # виджет разделитель
                Label(self.tab_2, text="  =  ", padx=25, pady=15).grid(row=len(self.spis), column=2)
                # виджет отвечающий за отображение % готовноости
                Label(self.tab_2, text=procent, relief=SOLID, pady=15, padx=25).grid(row=len(self.spis), column=3, sticky=E)
                self.spis[string] = str(len(self.tab_2.winfo_children() ) - 1) 
                logger.info("Создание виджета для отслеживания статууса закачки")

    @staticmethod
    def add_tags(filepath: str, title: str) -> object:
        """ Функция получив отдельно путь к папке с файлом и название самого файла
        В начале преобразует скаченную вместе с аудиофайлом картинку, из формата webp в формат jpg
        Разбирает название файла на две составляющие прежде разделенные знаком ' - ' где
        первая часть является псевдонимом исполнителя, а вторая название произведения
        Тегируют и вставляет преобразованную картинку в аудиофайл, а после удаляет весь кэш

            - filepath - absolute path to folder
            - title - filename 
        """

        imag = path.join(filepath, title + ".jpg")

        # попытка переупаковать изображения в jpg формат
        try:
            albumart = Image.open(filepath + "/" + title + ".webp")
            albumart.save(imag, "jpeg")
            logger.info("Картинка для обложки была успешно переупакованна")
        except IOError:
            albumart = imag
            logger.error("Ошибка при переупаковке изображения обложки")

        sound = path.join(filepath, title + ".mp3")
        image = path.join(filepath, title + ".jpg")
        audio = MP3(sound, ID3=ID3)

        # добавление обложки альбома
        logger.info("Добавление обложки альбома")
        audio.tags.add(
            APIC( encoding=3, mime='image/jpeg', type=3, desc=u'Cover', data=open(image, 'rb').read())
        )
        audio.save()


        # попытка удаления из папки webp и jpg изображения
        try:
            logger.info("Удаление из папки уже ненужной обложки...")
            [remove(d) if path.isfile(d := path.join(filepath, title + formats)) else print(d) for formats in ('.jpg', '.webp')]
        except:
            messagebox.showwarning("Ошибка удаления", "Почему-то картинка не удалилась!")
            logger.error("Удаление обложек из папки с аудифайлом привело к ошибке!")

        # добавление аудиотэгов к файлу
        logger.info("Добавление тэгов...")
        metatag = EasyID3(sound)
        info = title.rpartition("-")
        metatag["artist"] = info[0].strip().title()
        metatag["title"] = info[-1].strip().title()
        metatag.save()

    @staticmethod
    def rename(title: str) -> str:
        """ 
        - Преобразует название удаляя из него лишние символы и слова 
        - Ограничивает количество символом заменяя концовку троеточием ...
        """

        # набор удаляемых символов
        chars_filter = "()[]{}|:_/"
        # набор удаляемых слов
        words_filter = ["official", "lyrics", "audio", "remixed", "remix", "video", "full", "version", "music", "v8t", "hd", "hq", "uploaded", "explicit"]

        title = "".join(list(map(lambda x: "" if x in chars_filter else x, title)))
        title = [(itm if itm.lower() not in words_filter else "") for itm in title.split()]
        title = " ".join(filter(lambda x: x != "", title))
        return title[:70] + " ..." if len(title) > 60 else title[:]
        
    
    def input_validate(self, event):
        """ 
        - Если введена ссылка, то проводится проверка на корректность, при успешном исходе
        происходит парсинг параметров и создание виджета с ними

        - Если введено слово/а поиска, то происходит и парсинг первых пяти результатов по запросу  
        а после создание соответствующих виджетов
        """

        string = self.input_string.get().strip()
        self.clear()

        if string:
            # если пользователь ввел ссылку
            if any(string.startswith(item) for item in ["https://www.youtube.com", "https://youtu.be/"]):
                soup = bf(req.get(string).text, "html5lib").title
                name = self.rename(soup.string[:-10])
                self.button_configure( [{"name": name, "link": string}] )
            # если пользователь ввел поисковой запрос
            else:
                response = ys(string, max_results=5).to_dict()
                btn_attr = []
                for item in response:
                    name = self.rename(item["title"])
                    btn_attr.append({"name": name, "link": "https://www.youtube.com" + item["url_suffix"]})
                self.button_configure(btn_attr)
        else:
            messagebox.showerror("Ошибка ввода запроса", "Вы ничего не записали в поисковую строку!")
            logger.error("Возникла ошибка при проверке строки запроса")

if __name__ == "__main__":
    window = Window(600, 220, "DowYouMus.mp3")
    window.run()