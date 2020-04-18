
### Платформа для запуска скриптов под Windows на основе Python с горячими клавишами, меню в трее, HTTP-сервером и многим другим.

<p align="center">
	<img src="https://i6.imageban.ru/out/2019/07/04/a6f6538a80bc7a62ab06ce5cea295a93.png">
</p>

Исходный код: [https://github.com/vikilpet/Taskopy](https://github.com/vikilpet/Taskopy)

Привязать ваш код к горячей клавише или HTTP-запросу:

	def my_task(hotkey='ctrl+shift+t', http=True):
		print('Это моя задача!')

Теперь можно нажать Ctrl+Shift+T или открыть в браузере http://127.0.0.1:8275/task?my_task и задача будет выполнена.

Другой пример: показываем сообщение каждый день в 10:30 и скрываем из меню:

	def my_another_task(schedule='every().day.at("10:30")', menu=False):
		msgbox('Прими таблетки', ui=MB_ICONEXCLAMATION)

## Содержание
- [Установка](#установка)
- [Использование](#использование)
- [Свойства задачи](#свойства-задачи)
- [Настройки](#настройки)
- [Ключевые слова](#ключевые-слова)
	- [Общие](#общие)
	- [Клавиатура](#клавиатура)
	- [Файловая система](#файловая-система)
	- [Сеть](#сеть)
	- [Система](#система)
	- [Почта](#почта)
	- [Процессы](#процессы)
	- [Шифрование](#шифрование)
	- [Mikrotik RouterOS](#mikrotik-routeros)
	- [Winamp](#winamp)
- [Расширение для Firefox](#расширение-для-firefox)
- [Контекстное меню](#контекстное-меню)
- [Помочь проекту](#помощь-проекту)
- [Примеры задач](#примеры-задач)

## Установка
### Вариант 1: архив с исполняемым файлом.

**Требования:** Windows 7 и выше.
Вы можете [скачать](https://github.com/vikilpet/Taskopy/releases) zip архив (taskopy.zip), но многие не особо качественные антивирусы не любят Python, упакованный в exe, так что VirusTotal покажет примерно 7 срабатываний.

### Вариант 2: Python
**Требования:** Python 3.7+; Windows 7 и выше.

Скачайте проект, установите зависимости:

	pip install -r requirements.txt

Сделайте ярлык для taskopy.py и поместите в автозагрузку:

	%userprofile%\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\

В свойствах ярлыка выберите запуск минимизированным а так же смените иконку на resources\\logo.ico

## Использование
Откройте _crontab.py_ в вашем любимом текстовом редакторе и создайте задачу как функцию с аргументами:

	def demo_task_3('left_click'=True, log=False):
		app_start('calc.exe')

Затем кликните на иконке в трее и выберите _Reload crontab (перечитать кронтаб)_ и ваша задача готова.

## Свойства задачи
Свойства задачи это то, чтог вы помещаете в круглые скобочки после имени. Это ненастоящие аргументы для функции.

Формат: **название опции** (значение по умолчанию) — описание.

- **task_name** (None) — имя задачи. Можно использовать пробелы, русский язык и т.д.
- **menu** (True) — показывать в меню у иконки в трее.
- **hotkey** (None) — привязать к глобальной горячей клавише. Например: _hotkey='alt+ctrl+m'_
- **hotkey_suppress** (True) — не _съедать_ горячую клавишу, т.е. активное окно всё равно её получит.
- **schedule** (None) — запланированное задание. Функциональность обеспечивается модулем [schedule](https://github.com/dbader/schedule) так что лучше почитать их [документацию](https://schedule.readthedocs.io/en/stable/).
	Выполнять задачу каждый час:

		schedule='every().hour'

	Каждую среду в 13:15:

		schedule='every().wednesday.at("13:15")'

	Можно запланировать сразу несколько раз через список (каждую среду в 18:00 и каждую пятницу в 17:00):

		schedule=['every().wednesday.at("18:00")', 'every().friday.at("17:00")']

- **active** (True) — включить-выключить задачу.
- **startup** (False) — запускать при загрузке Taskopy.
- **sys_startup** (False) — запускать при загрузке Windows (время работы системы меньше 3 минут).
- **left_click** (False) — назначить на левый клик по иконке в трее.
- **log** (True) — логировать в консоль и в лог.
- **single** (True) — одновременно может выполняться только одна копия задачи.
- **submenu** (None) — разместить в подменю.
- **result** (False) — задача должна вернуть какое-то значение. Используется вместе с **http** опцией для выдачи результатов задачи.
- **http** (False) — запускать задачу через HTTP запрос. Синтаксис запроса: *http://127.0.0.1:8275/task?имя_задачи* где «имя_задачи» это название функции-задачи из crontab.
	Если свойство **result** также включено, то HTTP-запрос покажет то, что вернула задача или 'OK' если ничего не было возвращено.
	Пример:

		def demo_task_4(http=True, result=True):
			# Получить список файлов в папке Taskopy:
			listing = dir_list('*')
			# вернуть этот список как строку, разделённую br-тэгом.
			return '<br>'.join(listing)

	Результат в браузере:

		backup
		crontab.py
		log
		resources
		settings.ini
		taskopy.exe

	Смотрите в разделе [Настройки](#settings) про привязывание HTTP-сервера к IP и порту.
- **http_dir** - папка, куда сохранять файлы, отправленные через HTTP POST запрос. Если не указано - временная папка.
- **caller** - при указании в свойствах, в эту переменную будет записано, кто именно запустил задачу. Возможные варианты: http, menu, scheduler, hotkey. caller следует указывать перед другими свойствами задачи.
- **data** - для использования совместо с опцией **http**. Должен идти перед другими свойствами задачи. В эту переменную будут переданы данные из HTTP-запроса, так что с ними можно будет работать в тексте задачи, обращаясь как к свойству. Как минимум там будут содержаться:
	*data.client_ip* — IP-адрес того, кто выполнил запрос.
	*data.path* — весь относительный путь из URL, начиная с *task?*.
	*data.post_file* - путь к полученному файлу, который был отправлен задаче через POST запрос (смотрите **page_get**).
	Также в data будут содержаться стандартные HTTP-заголовки, такие как *User-Agent*, *Accept-Language* и т.д.
	Если в URL добавить какие-либо параметры согласно общепринятой схеме *param1=value1&param2=value2*, то они будут обработаны и также добавлены в data, таким образом вы можете обращаться к ним в теле задаче как *data.param1* и *data.param2*. Пример:

		def alert(data, http=True, single=False, menu=False):
			msgbox(
				data.text
				# Если есть, испльзовать data.title, иначе 'Alert'
				, title=data.title if data.title else 'Alert'
				, dis_timeout=1
			)
		
	После этого набираем в браузере такой запрос:
	http://127.0.0.1:8275/task?alert&text=MyMsg&title=MyTitle
	В результате чего будет выведено сообщение с заголовком *MyTitle* и текстом *MyMsg*.
- **idle** - выполнить задачу, когда пользователь бездействует указанное время. Например *idle='5 min'* — выполнить при бездействии в 5 минут. Задача выполняется только один раз в течении бездействия.
- **err_threshold** - не сообщать об ошибках в задаче, пока данный порог не будет превышен.

## Настройки
Глобальные настройки приложения хранятся в файле *settiings.ini*.

Формат: **настройка** (значение по умолчанию) — описание.

- **language** (en) — язык приложения. Варианты: en, ru.
- **editor** (notepad) — text editor for «Edit crontab» menu command.
- **hide_console** - скрыть окно консоли.
- **server_ip** (127.0.0.1) — привязать HTTP к этому локальному IP-адресу. Для разрешения ответа на запросы с любого адреса нужно указать *0.0.0.0*.
	**РАЗРЕШАТЬ ДОСТУП С ЛЮБОГО IP-АДРЕСА ПОТЕНЦИАЛЬНО ОПАСНО!** Не рекомендуется использовать *0.0.0.0* при подключении к публичным сетям, или ограничивайте доступ с помощью фаервола.
- **white_list** (127.0.0.1) — список IP-адресов через запятую, от которых принимаются запросы.
- **server_port** (8275) — порт HTTP-сервера.

## Ключевые слова
### Общие
- **balloon(msg:str, title:str=APP_NAME,timeout:int=None, icon:str=None)** - показывает сообщение у иконки в трее. `title` - 63 символа максимум, `msg` - 255 символов. `icon` - 'info', 'warning' или 'error'.
- **dialog(msg:str=None, buttons:list=None, title:str=None, content:str=None, default_button:int=0, timeout:int=None)->int** - показывает сообщение с несколькими кнопками. Возвращает ID нажатой кнопки, начиная с 1000.
	*buttons* - список строк с текстом на кнопках. Сколько строк, столько и кнопок.
	*title* - заголовок.
	*content* - дополнительный текст.
	*default_button* - номер кнопки, начиная с 1000, которая выбрана по умолчанию.
	*timeout* - таймаут, после которого сообщение закроется автоматически.
	Пример:

		dialog('Файл успешно скачан', ['Запустить', 'Скопировать путь', 'Отмена'], content='Источник файла: GitHub', timeout=60, default_button=2)

	![Dialog RU](https://user-images.githubusercontent.com/43970835/79643801-bc833300-81b5-11ea-8a2e-ea6baa045480.png)

- **jobs_batch(func_list:list, timeout:int)->list**: — запускает функции параллельно и ждёт, когда они закончат работу или истечёт таймаут. *func_list* — список со списками, где внутренний список должен содержать 3 элемента: функция, (args), {kwargs}. Возвращает список с DictToObj объектами *jobs*, которые иметю такие аттрибуты: func, args, kwargs, результат, время выполнения. Пример:

		func_list = [
			[function1, (1, 3, 4), {'par1': 2, 'par2':3}]
			, [function2, (), {'par1':'foo', 'par2':'bar'}]
			...
		]
		jobs:
		[
			<job.func=function1, job.args = (1, 3, 4), job.kwargs={'par1': 2, 'par2':3}
				, job.result=True, job.time='0:00:00.0181'>
			, <job.func=function2, job.args = (), job.kwargs={'par1':'foo', 'par2':'bar'}
				, job.result=[True, data], job.time='0:00:05.827'>

			...
		]
- **jobs_pool(function:str, pool_size:int, args:tuple)->list** - запускает функции по очереди, так чтобы одновременно выполнялось только `pool_size` функций. Если `pool_size` не указан, то он равен количеству процессоров в системе. Пример:

		jobs_pool(
			msgbox
			, (
				'one'
				, 'two'
				, 'three'
				, 'four'
			)
			, 4
		)
	
	Разница между `jobs_batch` и `job_pool`:
	- `jobs_batch` - разные функции с разными аргументами, ожидание работы функции прерывается через указанный таймаут и результаты возвращаются как есть, а где функция не успела выполниться - возвращается *timeout*. Все функции выполняются одновременно.
	- `jobs_pool` - одна и та же функция для набора аргументов, где количество аргументов совпадает. Одновременно выполняется только указанное количество экземпляров функции.
- **msgbox(msg:str, title:str=APP_NAME, ui:int=None, wait:bool=True, timeout=None)->int** - показать сообщение и вернуть код нажатой кнопки.
	Аргументы:
	*msg* — сообщение
	*title* — заголовок
	*ui* — [опции показа](https://docs.microsoft.com/en-us/windows/desktop/api/winuser/nf-winuser-messagebox)
		Пример: _ui = MB_ICONINFORMATION + MB_YESNO_
	*wait* — если *False* — продолжить выполнение задачи, не дожидаясь закрытия сообщения.
	*timeout* (число с секундами или строка с указанием единицы времени, например '1 hour', '5 min')— автоматически закрывать сообщение по истечении таймаута. Если сообщение закрыто по таймауту (пользователь не нажал никакую клавишу) и в _ui_ есть вариант с несколькими клавишами (например _MB_YESNO_) тогда сообщение вернёт 32000.
	*dis_timeout* (в секундах) — отключить кнопки на указанное количество секунд, чтобы было время подумать.
	Пример:

		def test_msgbox():
			if msgbox('Можно съесть пирожок?') == IDYES:
				print('Да!')
			else:
				print('Нельзя :-(')

	Если вам нужно сообщение с несколькими кнопками, смотрите **dialog**.

- **sound_play (fullpath:str, wait:bool)->str** - воспроизвести .wav файл. *wait* — ждать конца воспроизведения. Если *fullpath* это папка, значит проиграть случайный файл из неё.
- **time_diff(start, end, unit:str='sec')->int** - возвращает разницу между датами в выбранных единицах. *start* и *end* должны быть в формате datetime.
- **time_diff_str(start, end)->str** - возвращает разницу между датами в виде строки типа: '3:01:35'. *start* и *end* должны быть в формате datetime.
- **time_now()** - возвращает текущее время в формате datetime.
- **time_now_str(template:str='%Y-%m-%d\_%H-%M-%S')->str** - строка с текущей датой и временем.
- **pause(interval)** - приостановить выполнение задачи на указанное кол-во секунд. *interval* — время в секундах или строка с указанием единицы вроде '5 ms' или '6 sec' или '7 min'.
- **var_set(var_name:str, value:str)** - сохранить _значение_ переменной на диск. Таким образом можно хранить данные между запусками Taskopy.
- **var_get(var_name:str)->str** - получить значение переменной.
- **clip_set(txt:str)->** - поместить текст в буфер обмена.
- **clip_get()->str->** - получить текст из буфера обмена.
- **re_find(source:str, re_pattern:str, sort:bool=True)->list** - поиск в строке с помощью регулярного выражения. Возвращает список найденных значений.
- **re_match(source:str, re_pattern:str, re_flags:int=re.IGNORECASE)->bool** - соответствие регулярному выражению.
- **re_replace(source:str, re_pattern:str, repl:str='')** - заменить в строке всё найденное с помощью регулярного выражения на _repl._
- **inputbox(message:str, title:str, is_pwd:bool=False)->str** - показать сообщение с вводом текста. Возвращает введённую строку или пустую строку, если пользователь нажал отмену.
	*is_pwd* — скрыть вводимый текст.
- **random_num(a, b)->int** - вернуть случайное целое число в диапазоне от a до b, включая a и b.
- **random_str(string_len:int=10, string_source:str=None)->str** - сгенерировать строку из случайных символов заданной длины.

### Клавиатура

- **keys_pressed(hotkey:str)->bool** - нажата ли клавиша.
- **keys_send(hotkey:str)** - нажать сочетание клавиш.
- **keys_write(text:str)** - написать текст.

### Файловая система

**fullpath** означает полное имя файла, например 'c:\\\Windows\\\System32\\\calc.exe'

**ВАЖНО: всегда используйте двойной обратный слеш "\\\" в путях!**

- **csv_read(fullpath:str, encoding:str='utf-8', fieldnames=None, delimiter:str=';', quotechar:str='"')->list** - прочитать CSV файл и вернуть содержимое в виде списка со словарями.
- **csv_write(fullpath:str, content:list, fieldnames:tuple=None, encoding:str='utf-8', delimiter:str=';', quotechar:str='"', quoting:int=csv.QUOTE_MINIMAL)->str** - записывает список словарей как CSV файл. Если *fieldnames* не указан - берёт ключи первого словаря в качестве заголовков. Возвращает полный путь к файлу. Пример *content*:

		[
			{'name': 'some name',
			'number': 1}
			, {'name': 'another name',
			'number': 2}
			...	
		]
- **dir_copy(fullpath:str, destination:str)->int** - копировать папку и всё её содержимое. Возвращает количество ошибок при копировании.
- **dir_delete(fullpath:str):** - удалить папку.
- **dir_exists(fullpath:str)->bool** - папка существует?
- **dir_list(fullpath:str)->list:** - получить список файлов в папке.
	Примеры:
	- Получить список всех .log файлов в 'c:\\\Windows' **не учитывая** подпапки:

		dir_list('c:\\Windows\\*.log')

	- Получить список всех .log файлов в 'c:\\\Windows' **включая** подпапки:

		dir_list('c:\\Windows\\**\\*.log')

- **dir_size(fullpath:str, unit:str='b')->int** - размер папки в указанных единицах.
- **dir_zip(source:str, destination:str)->str** - упаковать папку в архив и вернуть путь к архиву.
- **drive_list()->list** - список логических дисков.
- **file_append(fullpath:str, content:str)->str** - дописывает *content* к файлу. Создаёт файл, если он не существует. Возвращает полное имя файла.
- **file_backup(fullpath:str, dest_dir:str='', now_format:str='_%y-%m-%d_%H-%M-%S')->str** - копировать 'somefile.txt' в 'somefile_2019-05-19_21-23-02.txt'. *dest_dir* - папка назначения. Если не указана - текущая папка файла. Возвращает полное имя нового файла.
- **file_basename(fullpath:str)->str** - возвращает *базовое* имя файла - без папки и расширения.
- **file_backup(fullpath, folder:str=None):** - сделать копию файла, дописав в имя текущую дату и время.
	*folder* — папка, куда следует поместить копию. Если не указано — поместить в папке оригинального файла.
- **file_copy(fullpath:str, destination:str):** - копировать файл. *destination* может быть папкой или полным путём к копии файла.
- **file_delete(fullpath:str):** - удалить файл.
- **file_dialog(title:str=None, multiple:bool=False, default_dir:str='', default_file:str='', wildcard:str='', on_top:bool=True)** - открывает стандартный диалог выбора файла. Возвращает полный путь или список полных путей, если _multiple_ == True.
- **file_dir(fullpath:str)->str:** - получить полное имя папки, в которой файл лежит.
- **file_exists(fullpath:str)->bool** - файл существует?
- **file_ext(fullpath:str)->str** - расширение файла без точки.
- **file_hash(fullpath:str, algorithm:str='crc32')->str**: - возвращает хэш файла. *algorithm* - 'crc32' или любой алгоритм из hashlib ('md5', 'sha512' и т.д.)
- **file_log(fullpath:str, message:str, encoding:str='utf-8', time_format:str='%Y.%m.%d %H:%M:%S')** - записать *message* в файл *fullpath*.
- **file_move(fullpath:str, destination:str):** - переместить файл.
- **file_name(fullpath:str)->str** - получить имя файла без папки.
- **file_name_add(fullpath:str, suffix:str='')->str** - добавляет строку (суффикс) к файлу перед расширением. Если суффикс не указан, добавляет строку из случайных символов. Пример: 
	
	>>> file_name_add('my_file.txt', '_1')
	'my_file_1.txt'

- **file_name_fix(fullpath:str, repl_char:str='\_')->str** - заменяет запрещённые символы на _repl_char_. Удаляет пробелы в начале и в конце. Добавляет '\\\\?\\' к длинным путям.
- **file_read(fullpath:str)->str:** - получить содержимое файла.
- **file_rename(fullpath:str, dest:str)->str** - переименовать файл. *dest* — полный путь или просто новое имя файла без папки.
- **file_size(fullpath:str, unit:str='b')->bool:** - получить размер файла (gb, mb, kb, b).
- **file_write(fullpath:str, content=str, encoding:str='utf-8')->str** - сохраняет *content* в файл. Создаёт файл, если он не существует. Если fullpath = '' или None, используется temp_file(). Возвращает полное имя файла.
- **file_zip(fullpath, destination:str)->str** - сжать файл или файлы в архив.
	*fullpath* — строка с полным именем файла или список с файлами.
	*destiniation* — полный путь к архиву.
- **drive_free(letter:str, unit:str='GB')->int:** - размер свободного места на диске (gb, mb, kb, b).
- **is_directory(fullpath:str)->bool:** - указанный путь является папкой?
- **path_exists(fullpath:str)->bool:** - указанный путь существует (не важно файл это или папка)?
- **dir_purge(fullpath:str, days:int=0, recursive=False, creation:bool=False, test:bool=False):** - удалить файлы из папки старше указанного числа дней.
	Если *days* == 0 значит удалить вообще все файлы в папке.
	*creation* — использовать дату создания, иначе использовать дату последнего изменения.
	*recursive* — включая подпапки.
	*test* — не удалять на самом деле, а просто вывести в консоль список файлов, которые должны быть удалены.
- **temp_dir(new_dir:str=None)->str** - возвращает путь ко временной папке. Если указана *new_dir* - создаёт подпапку во временной папке и возвращает её путь.
- **temp_file(suffix:str='')->str** - возвращает имя для временного файла.

### Сеть
- **domain_ip(domain:str)->list** - получить список IP-адресов по имени домена.
- **file_download(url:str, destination:str=None)->str:** - скачать файл и вернуть полный путь.
	*destination* — может быть *None*, полным путём к файлу или папкой. Если *None*, то скачать во временную папку и вернуть полное имя.
- **html_element(url:str, element, number:int=0)->str:** - получить текст HTML-элемента по указанной ссылке.
	*element* — словарь, который содержит информацию о нужном элементе (его имя, атрибуты); или список таких словарей; или строка с xpath.
	*number* - номер элемента, если таких находится несколько.
	Пример со словарём:

		# Получить внутренний текст элемента span, у которого есть
		# атрибут itemprop="softwareVersion"
		element={
			'name': 'span'
			, 'attrs': {'itemprop':'softwareVersion'}
		}
	
	Посмотрите на задачу *get_current_ip* в [Примеры задач](#task-examples)
- **html_clean(html_str:str, separator=' ')->str** - очищает строку от HTML тэгов.
- **is_online(*sites, timeout:int=2)->int:** - проверяет, есть ли доступ в Интернет, используя HEAD запросы к указанным сайтам. Если сайты не указаны, то использует google и yandex.
- **json_element(url:str, element:list):** - аналог **html_element** для JSON.
	*element* — список с картой для нахождения нужного элемента в структуре json.
	Пример: *element=['usd', 2, 'value']*
- **page_get(url:str, encoding:str='utf-8', post_file:str=None, post_hash:bool=False)->str:** - скачать указанную страницу и вернуть её содержимое. *post_file* - отправить указанный файл POST запросом. *post_hash* - в запросе указать хэш файла для проверки целостности (смотрите [Свойства задачи](#свойства-задачи)).
- **pc_name()->str** - имя компьютера.
- **url_hostname(url:str)->str** - извлечь имя домена из URL.

### Система
В функциях для работы с окнами аргумент *window* может быть или строкой с заголовком окна или числом, представляющим handle окна.

- **free_ram(unit:str='percent')** - количество свободной памяти. *unit* — 'kb', 'mb'... или 'percent'.
- **idle_duration(unit:str='msec')->int** - сколько прошло времени с последней активности пользователя.
- **monitor_off()** - выключить монитор.
- **registry_get(fullpath:str)** - получить значение ключа из реестра Windows.
	*fullpath* — строка вида 'HKEY_CURRENT_USER\\\Software\\\Microsoft\\\Calc\\\layout'
- **window_activate(window=None)->int** - вывести указанное окно на передний план. *window* может строкой с заголовком или числовым хэндлом нужного окна.
- **window_find(title:str)->list** - вернуть список хэндлов окон, с указанным заголовком.
- **window_hide(window=None)->int** - скрыть окно.
- **window_list(title_filter:str=None)->list** - список заголовков всех окон. *title_filter* - вернуть только заголовки с этой подстрокой.
**- window_on_top(window=None, on_top:bool=True)->int** - делает указанное окно поверх других окон.
- **window_show(window=None)->int** - показать окно.
- **window_title_set(window=None, new_title:str='')->int** -  найти окно по заголовку *cur_title* и поменять на *new_title*.

### Почта
- **mail_check(server:str, login:str, password:str, folders:list=['inbox'], msg_status:str='UNSEEN')->tuple** - возвращает количество новых писем и список ошибок.
- **mail_download(server:str, login:str, password:str, output_dir:str, folders:list=['inbox'], trash_folder:str='Trash')->tuple** - скачивает все письма в указанную папку. Успешно скачанные письма перемещаются в IMAP *trash_folder* папку на сервере. Возвращает список с декодированными заголовками писем и список с ошибками.
- **mail_send(recipient:str, subject:str, message:str, smtp_server:str, smtp_port:int, smtp_user:str, smtp_password:str)** - отправить письмо. Поддерживает отправку с русским заголовком и русским текстом.

### Процессы
- **app_start(app_path:str, app_args:str, wait:bool=False):** - запустить приложение. Если *wait=True* — возвращает код возврата, а если *False*, то возвращает PID созданного процесса.
	*app_path* — полный путь к исполняемому файлу.
	*app_args* — аргументы командной строки.
	*wait* — приостановить выполнение задачи, пока не завершится запущенный процесс.
- **file_open(fullpath:str):** - открыть файл или URL в приложении по умолчанию.
- **process_close(process, timeout:int=10, cmd_filter:str=None)** - мягкое завершение процесса: сначала закрываются все окна, принадлежащие указанному процессу, а по истечении таймаута (в секундах) убивается сам процесс, если ещё существует. *cmd_filter* - убивать только процессы, содержащие эту строку в командной строке.
- **process_exist(process, cmd:str=None)->bool** - проверяет, существует ли процесс и возвращает PID или False. *cmd* - необязательная строка для поиска в командной строке. Таким образом можно различать процессы с одинаковым исполняемым файлом но разной командной строкой.
- **process_list(name:str='', cmd_filter:str=None)->list —** получить список процессов. Список содержит объекты *DictToObj*, у которых есть следующие свойства:
	*pid* — числовой идентификатор.
	*name* — имя файла.
	*username* — имя пользователя.
	*exe* — полный путь к файлу.
	*cmdline* — комндная строка в виде списка.

	*cmd_filter* - фильтруем по наличию этой строки в командной строке.

	Пример — распечатать PID всех процессов Firefox:

		for proc in process_list('firefox.exe'):
			print(proc.pid)

- **process_cpu(pid:int, interval:int=1)->float** - процент загрузки процессора указанным PID. *interval* — время замера в секундах.
- **process_kill(process)** - убить указанный процесс. *process* может быть строкой с именем исполняемого файла, тогда будут завершены все процессы с таким названием, либо это может быть числовой PID, и тогда будет завершён только указанный процесс.
- **service_start(service:str, args:tuple=None)** - запускает службу.
- **service_stop(service:str)->tuple** - останавливает службу.
- **service_running(service:str)->bool** - служба запущена?
- **wts_message(sessionid:int, msg:str, title:str, style:int=0, timeout:int=0, wait:bool=False)->int** - отправляет сообщение терминальной сессии. *style* - стили как в msgbox (0 - MB_OK). *timeout* - таймаут в секундах (0 - без таймаута). Возвращает то же, что и msgbox.
- **wts_cur_sessionid()->int** - возвращает SessionID текущего процесса.
- **wts_logoff(sessionid:int, wait:bool=False)->int** - завершает терминальную сессию. *wait* - ждать завершения работы.
- **wts_proc_list(process:str=None)->list** - возвращает список объектов *DictToObj* с такими свойствами: *.sessionid:int*, *.pid:int*, *.process:str* (имя исполняемого файла), *.pysid:obj*, *.username:str*, *.cmdline:list*. *process* - фильтровать выдачу по имени процесса.
- **wts_user_sessionid(users, only_active:bool=True)->list** - преобразует список пользователей в список Session ID. *only_active* - вернуть только  WTSActive сессии.

### Шифрование
- **file_enc_write(fullpath:str, content:str, password:str, encoding:str='utf-8')**: — зашифровывает *content* и записывает в файл. Соль добавляется в виде расширения файла. Возвращает статус и полный путь/ошибку.
- **file_enc_read(fullpath:str, password:str, encoding:str='utf-8')->tuple**: — расшифровывает содержимое файла. Возвращает статус и содержимое/ошибку.
- **file_encrypt(fullpath:str, password:str)->tuple** - зашифровывает файл. Добавляет соль в виде расширения. Возвращает статус, полный путь/ошибку.
- **file_decrypt(fullpath:str, password:str)->tuple** - расшифровывает файл, возвращает статус и полный путь/ошибку.

### Mikrotik RouterOS
- **routeros_query(query:list, device_ip:str=None, device_port:str='8728', device_user:str='admin', device_pwd:str='')** - послать запрос на указанный маршрутизатор и вернуть результат. Запросы в API имеют специфический синтаксис, отличающийся от комманд для терминала, так что смотрите в [wiki](https://wiki.mikrotik.com/wiki/Manual:API).
	Пример — получить информацию об интерфейсе bridge1:

		status, data = routeros_query(
			[
				'/interface/print'
				, '?name=bridge1'
			]
			, '192.168.0.1'
			, '8728'
			, 'admin'
			, 'pAsSworD'
		)
	
	Содержимое *data*:

		[{'=.id': '*2',
		'=name': 'bridge1',
		'=type': 'bridge',
		'=mtu': 'auto',
		'=actual-mtu': '1500',
		'=l2mtu': '1596',
		'=mac-address': '6b:34:1B:2F:AA:21',
		'=last-link-up-time': 'jun/10/2019 10:33:35',
		'=link-downs': '0',
		'=rx-byte': '1325381950539',
		'=tx-byte': '2786508773388',
		'=rx-packet': '2216725736',
		'=tx-packet': '2703349720',
		'=rx-drop': '0',
		'=tx-drop': '0',
		'=tx-queue-drop': '0',
		'=rx-error': '0',
		'=tx-error': '0',
		'=fp-rx-byte': '1325315798948',
		'=fp-tx-byte': '0',
		'=fp-rx-packet': '2216034870',
		'=fp-tx-packet': '0',
		'=running': 'true',
		'=disabled': 'false',
		'=comment': 'lan'}]

- **routeros_send(cmd:str, device_ip:str=None, device_port:str='8728', device_user:str='admin', device_pwd:str='')** - отправить команду на указанный маршрутизатор и получить статус выполнения и ошибку, если есть.
	Пример: сначала получаем список постоянных («dynamic=false») записей в списке адресов «my_list», а затем удаляем все найденные записи:

		status, data = routeros_query(
			[
				'/ip/firewall/address-list/print'
				, '?list=my_list'
				, '?dynamic=false'
			]
			, device_ip='192.168.0.1'
			, device_user='admin'
			, device_pwd='PaSsWorD'
		)
		
		# проверить статус выполнения запроса и выйти, если ошибка:
		if not status:
			print(f'Ошибка: {data}')
			return
		
		# получаем список номеров всех записей:
		items = [i['=.id'] for i in data]
		
		# Теперь отправляем команду на удаление всех найденных номеров.
		# Обратите внимание: команда в данном случае это список с командами
		routeros_send(
			[
				[
					'/ip/firewall/address-list/remove'
					, f'=.id={i}'
				] for i in items
			]
			, device_ip='192.168.0.1'
			, device_user='admin'
			, device_pwd='PaSsWorD'
		)
	
- **routeros_find_send(cmd_find:list, cmd_send:list, device_ip:str=None, device_port:str='8728', device_user:str='admin', device_pwd:str='')** - комбинированное слово для операций, требующих предварительного поиска номеров (*find* в терминале)
	*cmd_find* — список с командами для поиска значений.
	*cmd_send* — команда, которая будет выполняться для найденных элементов.
	Пример — удаление всех статических адресов из address-list:

		status, data = routeros_find_send(
			cmd_find=[
				'/ip/firewall/address-list/print'
				, '?list=my_list'
				, '?dynamic=false'
			]
			, cmd_send=['/ip/firewall/address-list/remove']
			, device_ip='192.168.88.1'
			, device_user='admin'
			, device_pwd='PasSWoRd'
		)

### Winamp
- **winamp_close** - закрыть Винамп.
- **winamp_fast_forward** - перемотка на 5 секунд вперёд.
- **winamp_fast_rewind** - перемотка на 5 секунд назад.
- **winamp_notification():** - показать уведомление (только для скина «Modern»).
- **winamp_pause():** - пауза.
- **winamp_play():** - воспроизведение.
- **winamp_status()->str:** - статус воспроизведения ('playing', 'paused' или 'stopped').
- **winamp_stop():** - остановить.
- **winamp_toggle_always_on_top** - установить/снять окно поверх всех окон.
- **winamp_toggle_main_window** - показать/скрыть окно Винампа.
- **winamp_toggle_media_library** - показать/скрыть окно библиотеки.
- **winamp_track_info(sep:str='   ')->str:** - получить строку с частотой, битрейтом и количеством каналов у текущего трека. *sep* — разделитель.
- **winamp_track_length()->str:** - длина трека.
- **winamp_track_title(clean:bool=True)->str:** - название текущего трека.

## Расширение для Firefox
https://addons.mozilla.org/ru/firefox/addon/send-to-taskopy/

Расширение просто добавляет пункт в контекстное меню. С помощью него можно запустить задачу из Taskopy. В переменную _data_ задачи передаётся (если есть):
	- data.page_url - URL текущей страницы
	- data.link_url - URL ссылки, на которой кликнули
	- data.editable - элемент редактируемый?
	- data.selection - текст выделения
	- data.media_type - вид объекта (изображение, видео)
	- data.src_url - ссылка источник объекта.

Свойство _editable_ логическое, остальные строковые.

В настройках расширения указываете URL вашей задачи, которая будет обрабатывать данные, например:

	http://127.0.0.1:8275/task?get_data_from_browser

У этой задачи должны быть указаны _data_ и _http=True_

Пример задачи для проигрывания Youtube видео в PotPlayer:

	def get_data_from_browser(data, http=True, menu=False, log=False):
		if ('youtube.com' in data.link_url
		or 'youtu.be' in data.link_url):
			app_start(
				r'c:\Program Files\DAUM\PotPlayer\PotPlayerMini64.exe'
				, data.link_url
			)

## Контекстное меню
Можно добавить Taskopy в подменю *Отправить* контекстного меню файлов.

В папке *resources* есть простой powershell скрипт *Taskopy.ps1* Вам нужно создать ярлык на этот файл в папке пользователя:

	%APPDATA%\Microsoft\Windows\SendTo\

По умолчанию имя задачи это _send\_to_. Эта задача должна иметь свойства _data_ и _http_, так что внутри задачи имя файла доступно в виде _data.fullpath_

Пример - передаём полный путь файла в задачу _virustotal\_demo_ из [Примеры задач](#примеры-задач):

	def send_to(data, http, menu=False, log=False):
		if file_ext(data.fullpath) in ['exe', 'msi']:
			virustotal_demo(data.fullpath)

В самой задаче _virustotal\_demo_ можно увидеть другой способ передачи файла в задачу - через **file_dialog**.

## Помощь проекту
- [Мой вопрос на StackOverflow про показ меню по горячей клавише.](https://stackoverflow.com/questions/56079269/wxpython-popupmenu-by-global-hotkey) Если у вас есть знакомый эксперт по wxPython, пришлите ему эту ссылку, или добавьте награду, если ваш рейтинг позволяет.
- Расскажите о Taskopy друзьям.

## Примеры задач
- iPython + Taskopy
- Свободное место на дисках
- Текущий IP адрес
- Добавление IP-адреса в маршрутизатор MikroTik
- Калькулятор и курс валют
- Проверка на Virustotal

Запуск iPython (Jupyter) и загрузка кронтаба для быстрого доступа ко всем функциям из плагинов:

	def iPython(on_load=False, submenu='WIP'
	, task_name='iPython + Taskopy'):
		TASKOPY_DIR = r'd:\soft\taskopy'
		process_kill('ipython.exe')
		file_open('ipython')
		for _ in range(100):
			if 'ipython' in window_title_get().lower():
				break
			pause('100 ms')
		pause(1)
		if not 'ipython'.lower() in window_title_get().lower():
			tprint('ipython not found')
			return
		keys_write('%cd ' + TASKOPY_DIR)
		keys_send('enter')
		keys_write(
			r'%load_ext autoreload' + '\n'
			+ r'%autoreload 2' + '\n'
			+ 'from crontab import *\n'
		)
		pause('200 ms')
		keys_send('ctrl+enter')
	
Проверяем свободное место на всех дисках. Планируем выполнение случайный интервал между 30 и 45 минутами:

	def check_free_space_demo(submenu='demo'
	, schedule='every(30).to(45).minutes'):
		for d in drive_list():
			if drive_free(d) < 10:
				msgbox(f'Осталось мало места: {d}')

Показываем сообщение с текущим внешним IP-адресом с помощью сервиса dyndns.org:

	def get_current_ip_demo(submenu='demo'):
		# Получаем текст HTML-тэга 'body' со страницы checkip.dyndns.org
		# html_element вернёт строку вроде 'Current IP Address: 11.22.33.44'
		ip = html_element(
			'http://checkip.dyndns.org/'
			, {'name': 'body'}
		).split(': ')[1]
		tprint(f'Текущий IP: {ip}')
		msgbox(f'Текущий IP: {ip}', timeout=10)

Добавить IP-адрес из буфера обмена в список адресов маршрутизатора MikroTik:

	def add_ip_to_list_demo(submenu='demo'):
		routeros_send(
			[
				'/ip/firewall/address-list/add'
				, '=list=my_list'
				, '=address=' + clip_get()
			]
			, device_ip='192.168.88.1'
			, device_user='admin'
			, device_pwd='PaSsWoRd'
		)
		msgbox('Готово!', timeout=5)

Запускаем калькулятор и меняем его заголовок на курс продажи доллара в Сбербанке. Назначаем выполнение задачи на клик левой клавишей мыши по иконке:

	def calc_usd_demo(left_click=True, submenu='demo'):
		# Запускаем калькулятор:
		app_start(r'calc.exe')
		# Скачиваем json, по которому грузится список валют
		# и получаем из него курс продажи доллара:
		usd = json_element(
			'https://www.sberbank.ru/portalserver/proxy/?pipe=shortCachePipe&url=http://localhost/rates-web/rateService/rate/current%3FregionId%3D77%26currencyCode%3D840%26currencyCode%3D978%26rateCategory%3Dbeznal'
			, ['beznal', '840', '0', 'sellValue']
		)
		# Теперь меняем заголовок калькулятора на USD={найденное значение}
		window_title_set('Калькулятор', f'USD={usd}')

Проверяем MD5 хеш файла на Virustotal. Вам нужно будет зарегистрироваться там, чтобы получить бесплатный API ключ:

	def virustotal_demo(fullpath:str=None, submenu='demo'):
		APIKEY = 'ваш API ключ'
		if not fullpath:
			fullpath = file_dialog('Virustotal', wildcard='*.exe;*.msi')
			if not fullpath:
				return
		md5 = file_hash(fullpath, 'md5')
		scan_result = json_element(f'https://www.virustotal.com/vtapi/v2/file/report?apikey={APIKEY}&resource={md5}')
		if isinstance(scan_result, Exception):
			tprint(scan_result)
			msgbox('Ошибка HTTP-запроса')
			return
		if scan_result['response_code'] == 0:
			msgbox('Неизвестный файл', timeout=3)
			return
		res = DictToObj(scan_result)
		for av in res.scans.keys():
			if res.scans[av]['detected']:
				print(f'{av}: ' + res.scans[av]['result'])
		msgbox(f'Результат: {res.positives} из {res.total}', timeout=5)

Получаем файл через HTTP POST запрос и выводим сообщение с комментарием и полным именем файла:

	def http_post_demo(data, http=True, log=False, menu=False):
		dialog(f'{data.filecomment}\n\n{data.post_file}')

Пример отправки запроса в задачу:

	curl -F "filecomment=Take this!" -F "file=@d:\my_picture.jpg" http://127.0.0.1:8275/task?http_post_demo
