

### Платформа для запуска скриптов под Windows на основе Python с горячими клавишами, меню в трее, HTTP-сервером и многим другим.

<p align="center">
	<img src="https://i6.imageban.ru/out/2019/07/04/a6f6538a80bc7a62ab06ce5cea295a93.png">
</p>

Исходный код: [https://github.com/vikilpet/Taskopy](https://github.com/vikilpet/Taskopy)

Привязать ваш код к горячей клавише или HTTP-запросу:

	def my_task(hotkey='ctrl+shift+t', http=True):
		print('Это моя задача!')

Теперь можно нажать Ctrl+Shift+T или открыть в браузере http://127.0.0.1:8275/my_task и задача будет выполнена.

Другой пример: показываем сообщение каждый день в 10:30 и скрываем из меню:

	def my_another_task(every='day 10:30', menu=False):
		dialog('Прими таблетки')

Пример с использованием расширения для Firefox:

[![Taskopy + PotPlayer + youtube-dl](https://img.youtube.com/vi/LPMzMv8f9H0/0.jpg)](https://www.youtube.com/watch?v=LPMzMv8f9H0)

Использование вместе с Total Commander:

[![Taskopy + Total Commander](https://img.youtube.com/vi/IAkXV_XJyfY/0.jpg)](https://www.youtube.com/watch?v=IAkXV_XJyfY)

Отслеживание изменений в автозагрузке Windows:

[![Taskopy + Autoruns vs Firefox browser agent](https://img.youtube.com/vi/bUIVBRI3hBg/0.jpg)](https://youtu.be/bUIVBRI3hBg)

Удаленное управление:

[![PotPlayer remote control](https://img.youtube.com/vi/_FTuEid0Q7U/0.jpg)](https://youtu.be/_FTuEid0Q7U)

Чат в Телеграме: https://t.me/taskopy_g

## Содержание

- [Установка](#установка)
	- [Вариант 1: архив с исполняемым файлом.](#вариант-1-архив-с-исполняемым-файлом)
	- [Вариант 2: Python](#вариант-2-python)
- [Использование](#использование)
- [Свойства задачи](#свойства-задачи)
- [Настройки](#настройки)
- [Ключевые слова](#ключевые-слова)
	- [Разное](#разное)
	- [Клавиатура](#клавиатура)
	- [Файловая система](#файловая-система)
	- [Сеть](#сеть)
	- [Система](#система)
	- [Почта](#почта)
	- [Процессы](#процессы)
	- [Шифрование](#шифрование)
	- [Mikrotik RouterOS](#mikrotik-routeros)
- [Полезные советы](#полезные-советы)
- [Расширение для Firefox](#расширение-для-firefox)
- [Контекстное меню](#контекстное-меню)
- [Помощь проекту](#помощь-проекту)
- [Примеры задач](#примеры-задач)

## Установка

### Вариант 1: архив с исполняемым файлом.

**Требования:** Windows 7 и выше.
Вы можете [скачать](https://github.com/vikilpet/Taskopy/releases) zip архив (taskopy.zip)

### Вариант 2: Python

**Требования:** Python 3.7+; Windows 7 и выше.  
Скачайте проект, установите зависимости:

	pip install -r requirements.txt

Примечание 1: *wxPython* требует *Pillow*, но [Pillow > 9.5.0 больше не включает 32-битные колеса](https://pillow.readthedocs.io/en/latest/installation.html#basic-installation), поэтому установите 9.5.0:

	pip install Pillow==9.5.0

Примечание 2: для совместимости с Windows 7 используется модуль *cryptography* версии 42.0.8

Создайте ярлык *taskopy.py* в папке запуска пользователя со встроенной задачей *Add to startup*.

## Использование
Откройте _crontab.py_ в вашем любимом текстовом редакторе и создайте задачу как функцию с аргументами:

	def demo_task_3('left_click'=True, log=False):
		proc_start('calc.exe')

Затем кликните на иконке в трее и выберите *Reload crontab (перечитать кронтаб)* и ваша задача готова.

## Свойства задачи
Свойства задачи это то, что вы помещаете в круглые скобочки после имени. Это ненастоящие аргументы для функции.

Формат: **название опции** (значение по умолчанию) — описание.

- **date** (None) - дата и время для выполнения задачи, например '2020.09.01 22:53'. Можно использовать '*' вместо числа, чтобы запускать каждый год или месяц и т.п. Примечание: задача будет запущена не ровно в первую секунду указанной минуты.
- **event_log** (None) - название журнала Windows (System, Application, Security, Setup), т.е. выполнять задачу при новых событиях в этом журнале. Для тестирования можно создать новое событие в журнале Application в консоли от админа:

	eventcreate /ID 174 /L Application /T Information /D "Test"

	Если у задачи есть аргумент *data* то ему будет назначена информация о событии в формате *DataEvent*. Пример задачи:

		def windows_errors(
			event_log = 'System'
			, event_xpath = '*[System[Level < 4]]'
			, data:DataEvent = None
			, menu=False, log=False
		):
			balloon(f'Event (ID {data.EventID}): {data.Provider}\n{data.TimeCreated}')

- **event_xpath** ('*') - XPath для отфильтровывания нужных событий. Регистр имеет значение. Например:

	event_xpath='*[System[Level < 4]]' - только для событий журнала Система с уровнем меньше четырёх.

- **task_name** (None) — имя задачи. Можно использовать пробелы, русский язык и т.д.
- **menu** (True) — показывать в меню у иконки в трее.
- **hotkey** (None) — привязать к глобальной горячей клавише. Например: _hotkey='alt+ctrl+m'_
- **hotkey_suppress** (True) — не _съедать_ горячую клавишу, т.е. активное окно всё равно её получит.
- **hyperactive** — запуск задачи, даже если Taskopy отключен.
- **every** ('') — запускать по расписанию.  
	Примеры:  
	Запускать задачу каждые 5 минут:

		every='5 min'

	Каждый час в 30 минут:

		every='hour :30'

	Каждую среду в 13:15:

		every='wed 13:15'
	
	Каждый день в 08:30:

		every='day 08:30'

	Можно указать несколько вариантов в кортеже:

		every=('wed 18:00', 'fri 17:00')

	Примечание: задачи запускаются не ровно в 0 секунд, а в секунду, в которую был загружен/перезагружен кронтаб.

- **active** (True) — включить-выключить задачу.
- **startup** (False) — запускать при загрузке Taskopy.
- **sys_startup** (False) — запускать при загрузке Windows (время работы системы меньше 3 минут).
- **left_click** (False) — назначить на левый клик по иконке в трее.
- **log** (True) — логировать в консоль и в лог.
- **rule** (None) — функция или кортеж функций. Если функция возвращает `False`, задача не выполняется. Эта проверка не осуществляется, если задача запускается из меню в системном трее.
- **single** (True) — одновременно может выполняться только одна копия задачи.
- **submenu** (None) — разместить в подменю.
- **result** (False) — задача должна вернуть какое-то значение. Используется вместе с **http** опцией для выдачи результатов задачи.
- **http** (False) — запускать задачу через HTTP запрос. Синтаксис запроса: *http://127.0.0.1:8275/имя_задачи* где «имя_задачи» это название функции-задачи из *crontab*, *8275* - порт по умолчанию.

	Этот параметр так же может принимать строку с паттерном регулярного выражения или кортеж таких строк.

		http=(r'task_\w+', r'task_\d+')

	Таким образом, задача отображения текста при переходе в корень *сайта* будет выглядеть следующим образом:

		def http_root(http='^$', result=True):
			return 'Это корень'

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

	Если у задачи есть *data* аргумент, то в него будет передана информация о запросе в виде объекта *DataHTTPReq*.

	Смотрите в разделе [Настройки](#settings) про привязывание HTTP-сервера к IP и порту.
- **http_dir** — папка, куда сохранять файлы, отправленные через HTTP POST запрос. Если не указано - временная папка.
- **http_white_list** — белый список IP адресов только для этой задачи. Пример:
	
		http_white_list=['127.0.0.1', '192.168.0.*']

- **on_dir_change** — запускать задачу при появлении изменений в папке:

		def demo__on_dir_change(on_dir_change=temp_dir()
		, data:tuple=None, active=True):
			fpath, action = data
			tprint(f'{action}: {fpath}')

- **on_exit** — запускать задачу при выходе из Taskopy. Обратите внимание, что Taskopy не будет закрыт, пока эти задачи не будут выполнены.
- **on_file_change** — запускать задачу при изменении файла.
- **caller** — при указании в свойствах, в эту переменную будет записано, кто именно запустил задачу. Возможные варианты: 'http', 'menu', 'scheduler', 'hotkey' и т.д. caller следует указывать перед другими свойствами задачи.
- **data** — для того, чтобы передать в задачу какие-либо данные, например *DataEvent* или *DataHTTPReq*.
- **idle** — выполнить задачу, когда пользователь бездействует указанное время. Например *idle='5 min'* — выполнить при бездействии в 5 минут. Задача выполняется только один раз в течении бездействия.
- **err_threshold** — не сообщать об ошибках в задаче, пока данный порог не будет превышен.

## Настройки
Глобальные настройки приложения хранятся в файле *settiings.ini*.

Формат: **настройка** (значение по умолчанию) — описание.

- **language** (en) — язык приложения. Варианты: en, ru.
- **editor** (notepad) — text editor for «Edit crontab» menu command.
- **hide_console** — скрыть окно консоли.
- **server_ip** (127.0.0.1) — привязать HTTP к этому локальному IP-адресу. Для разрешения ответа на запросы с любого адреса нужно указать *0.0.0.0*.
	**РАЗРЕШАТЬ ДОСТУП С ЛЮБОГО IP-АДРЕСА ПОТЕНЦИАЛЬНО ОПАСНО!** Не рекомендуется использовать *0.0.0.0* при подключении к публичным сетям, или ограничивайте доступ с помощью фаервола.
- **white_list** (127.0.0.1) — глобальный список IP-адресов через запятую, с которых разрешены HTTP запросы.
- **server_port** (8275) — порт HTTP-сервера.

## Ключевые слова

### Разное

- **app_enable()** — включение приложения.
- **app_disable()** — отключение приложения. Запуск задачи по-прежнему возможен через меню иконки.
- **balloon(msg:str, title:str=APP_NAME,timeout:int=None, icon:str=None)** — показывает сообщение у иконки в трее. `title` - 63 символа максимум, `msg` - 255 символов. `icon` - 'info', 'warning' или 'error'.
- **benchmark(func, b_iter:int=1000, a:tuple=(), ka:dict={})->datetime.timedelta** — выполняет футкцию `func` `b_iter` раз и выводит время выполнения. Пример:

		benchmark(dir_size, b_iter=100, a=('logs',) )

- **crontab_reload()** — перезагружает кронтаб.
- **dialog(msg:str=None, buttons:list=None, title:str=None, content:str=None, default_button:int=0, timeout:int=None, return_button:bool=False)->int** — показывает сообщение с несколькими кнопками. Возвращает ID нажатой кнопки, начиная с 1000.
	*buttons* - список строк с текстом на кнопках. Сколько строк, столько и кнопок.
	*title* - заголовок.
	*content* - дополнительный текст.
	*default_button* - номер кнопки, начиная с 1000, которая выбрана по умолчанию.
	*timeout* - таймаут, после которого сообщение закроется автоматически.
	Пример:

		dialog('Файл успешно скачан', ['Запустить', 'Скопировать путь', 'Отмена'], content='Источник файла: GitHub', timeout=60, default_button=2)

	![Dialog RU](https://user-images.githubusercontent.com/43970835/79643801-bc833300-81b5-11ea-8a2e-ea6baa045480.png)

- **exc_name()->str** — возвращает только имя исключения:

		try:
			0 / 0
		except:
			asrt(exc_name(), 'ZeroDivisionError')

		asrt( benchmark(exc_name), 521, "<" )

- **hint(text:str, position:tuple=None)->int** — показывает небольшое окошко с указанным текстом. Только для *Python* версии. *position* - кортеж с координатами. Если координаты не указаны - появится в центре экрана. Возвращает PID процесса с окошком.
- **HTTPFile** — Используйте этот класс, если ваша HTTP задача возвращает файл:

		def http_file_demo(http=True, result=True
		, submenu='demo'):
			# http://127.0.0.1:8275/http_file_demo
			return HTTPFile(
				fullpath=r'resources\icon.png'
				, use_save_to=True
			)

- **is_often(ident, interval)->bool** — не происходит ли какое-то событие слишком часто?  
	Цель - не беспокоить пользователя слишком частыми оповещениями о событиях.  
	*ident* - уникальный идентификатор события.  
	*interval* - интервал измерения, не менее 1 мс.  

		is_often('_', '1 ms')
		asrt( is_often('_', '1 ms'), True)
		time_sleep('1 ms')
		asrt( is_often('_', '1 ms'), False)
		asrt( benchmark(is_often, ('_', '1 ms')), 5000, "<" )

- **Job(func, args, job_name:str='', kwargs)** — класс для параллельного запуска функций в *job_batch* и *job_pool*. Свойства:
	- *result* - результат выполнения функции
	- *time* - время в секундах
	- *error* - произошла ошибка
- **job_batch(jobs:list, timeout:int)->list**: — запускает функции параллельно и ждёт, когда они закончат работу или истечёт таймаут. *jobs* — список с объектами типа **Job**. Используйте job_batch, когда вы не хотите долго ждать, если одна из выполняемых функций зависла.

	Пример - создаём список из двух заданий с *dialog*, с разными параметрами:

		jobs = []
		jobs.append(
			Job(dialog, 'Test job 1', timeout=10)
		)
		jobs.append(
			Job(dialog, ['Button 1', 'Button 2'])
		)
		for job in job_batch(jobs, timeout=5):
			print(job.error, job.result, job.time)

- **job_pool(jobs:list, pool_size:int, args:tuple)->list** — запускает задания (Job) по очереди, так чтобы одновременно выполнялось только `pool_size` заданий. Если `pool_size` не указан, то он равен количеству процессоров в системе.

	Пример:

		jobs = []
		jobs.append(
			Job(dialog, 'Test job 1', timeout=10)
		)
		jobs.append(
			Job(dialog, ['Button 1', 'Button 2'])
		)
		jobs.append(
			Job(dialog, 'Third job')
		)
		for job in job_pool(jobs, pool_size=2):
			print(job.error, job.result, job.time)

	Разница между `job_batch` и `job_pool`:
	- `job_batch` - все задания запускаются одновременно. Если какое-то задание не выполняется за указанный таймаут, оно возвращается с ошибкой (job.error = True, job.result = 'timeout').
	- `job_pool` - одновременно выполняется только указанное количество заданий.
- **msgbox(msg:str, title:str=APP_NAME, ui:int=None, wait:bool=True, timeout=None)->int** — показать сообщение и вернуть код нажатой кнопки.
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

- **safe** — function wrapper for safe execution.
	Пример:

		func(arg) -> result

	С использованием *safe*:

		safe(func)(arg) -> True, result
		OR
		safe(func)(arg) -> False, Exception

- **sound_play (fullpath:str, wait:bool)->str** — воспроизвести .wav файл. *wait* — ждать конца воспроизведения. Если *fullpath* это папка, значит проиграть случайный файл из неё.
- **str_diff(text1:str, text2:str)->tuple[tuple[str]]** — возвращает различные строки между двумя текстами (т.е. строки с **переносами**) в виде кортежа кортежей.

		tass(
			tuple(str_diff('foo\nbar', 'fooo\nbar'))
			, (('foo', 'fooo'),)
		)
		# Different new line symbols are ok:
		tass( tuple(str_diff('same\r\nlines', 'same\nlines') ), () )
		# Note no difference here:
		tass( tuple(str_diff('same\nlines', 'lines\nsame') ), () )

- **str_short(text:str, width:int=0, placeholder:str='...')->str** — свернуть и усечь заданный текст, чтобы он поместился в заданную ширину.  
	Сначала удаляются непечатные символы. Если после этого строка укладывается в указанную ширину, она возвращается. В противном случае, как можно больше слов соединяется , а затем добавляется заполнитель.  
	Если *ширина* не указана, используется текущая ширина терминала.

		tass( str_short('Hello,  world! ', 13), 'Hello, world!' )
		tass( str_short('Hello,  world! ', 12), 'Hello,...' )
		tass( str_short('Hello\nworld! ', 12), 'Hello world!' )
		tass( str_short('Hello\nworld! ', 11), 'Hello...' )
		tass( benchmark(str_short, ('Hello,  world! ',)), 60_000, '<')

- **time_diff(start, end, unit:str='sec')->int** — возвращает разницу между датами в выбранных единицах. *start* и *end* должны быть в формате datetime.
- **time_diff_str(start, end)->str** — возвращает разницу между датами в виде строки типа: '3:01:35'. *start* и *end* должны быть в формате datetime.
- **time_now(\*\*delta)->datetime.datetime** — возвращает объект datetime. Используйте ключевые слова `datetime.timedelta` для получения другого времени. Вчера:

		time_now(days=-1)
		
- **time_now_str(template:str='%Y-%m-%d\_%H-%M-%S')->str** — строка с текущей датой и временем.
- **toast(msg:str|tuple|list, dur:str='default', img:str='', often_ident:str='', often_inter:str='30 sec', on_click:Callable=None, appid:str=APP_NAME)** — Тост-уведомление.  
	*img* - полный путь к изображению.  
	*duration* - 'short'|'long'|'default'. 'long' is about 30 sec.  
	*on_click* - действие, выполняемое при нажатии. Ему передается аргумент со свойствами клика. Если уведомление уже исчезло с экрана и находится в Центре Уведомлений, действие будет выполнено, только если указан действительный *appid*.  
	*appid* - пользовательский AppID. Если вы хотите, чтобы тост имел иконку Taskopy, выполните задачу `emb_appid_add` из *ext_embedded*.  

- **pause(interval)** — приостановить выполнение задачи на указанное кол-во секунд. *interval* — время в секундах или строка с указанием единицы вроде '5 ms' или '6 sec' или '7 min'.
- **var_lst_get(var:str, default=[], encoding:str='utf-8', com_str:str='#')->list** — возвращает список со строками. Исключает пустые строки и строки, начинающиеся с *com_str*

		var_lst_set('test', ['a', 'b'])
		assert var_lst_get('test') == ['a', 'b']
		var_lst_set('test', map(str, (1, 2)))
		assert var_lst_get('test') == ['1', '2']
		assert var_del('test') == True

- **var_lst_set(var, value, encoding:str='utf-8')** — устанавливает переменную *дисковую переменную со списком*.

		# Обратите внимание на то, что число стало строкой:
		var_lst_set('test', ['a', 'b', 1])
		assert var_lst_get('test') == ['a', 'b', '1']
		assert var_del('test')

- **var_set(var_name:str, value:str)** — сохранить _значение_ переменной на диск. Таким образом можно хранить данные между запусками Taskopy.
	
		var_set('test', 5)
		assert var_get('test') == '5'
		assert var_del('test') == True

		# Составное имя переменной
		# промежуточные папки будут созданы:
		var = ('file', 'c:\\pagefile.sys')
		var_set(var, 1)
		assert var_get(var, 1) == '1'
		assert var_del(var) == True

- **var_get(var_name:str)->str** — получить значение переменной.

	*as_literal* - преобразуется в литерал (dict, list, tuple и т.д.).
	Опасно! - это просто **eval**, а не **ast.literal_eval**

		var_set('test', 1)
		assert var_get('test') == '1'
		assert var_get('test', as_literal=True) == 1
		assert var_del('test') == True

- **clip_set(txt:str)->** — поместить текст в буфер обмена.
- **clip_get()->str->** — получить текст из буфера обмена.
- **re_find(source:str, re_pattern:str, sort:bool=True)->list** — поиск в строке с помощью регулярного выражения. Возвращает список найденных значений.
- **re_match(source:str, re_pattern:str, re_flags:int=re.IGNORECASE)->bool** — соответствие регулярному выражению.
- **re_replace(source:str, re_pattern:str, repl:str='')** — заменить в строке всё найденное с помощью регулярного выражения на _repl._
- **re_split(source:str, re_pattern:str, maxsplit:int=0, re_flags:int=re.IGNORECASE)->List[str]** — разделение по регулярному выражению:
	
		tass( re_split('abc', 'b'), ['a', 'c'] )
	
- **inputbox(message:str, title:str, is_pwd:bool=False)->str** — показать сообщение с вводом текста. Возвращает введённую строку или пустую строку, если пользователь нажал отмену.
	*is_pwd* — скрыть вводимый текст.
- **random_num(a, b)->int** — вернуть случайное целое число в диапазоне от a до b, включая a и b.
- **random_str(string_len:int=10, string_source:str=None)->str** — сгенерировать строку из случайных символов заданной длины.

### Клавиатура

- **key_pressed(hotkey:str)->bool** — нажата ли клавиша.
- **key_send(hotkey:str)** — нажать сочетание клавиш.
- **key_write(text:str)** — написать текст.

### Файловая система

**fullpath** означает полное имя файла, например 'c:\\\Windows\\\System32\\\calc.exe'

**ВАЖНО: всегда используйте двойной обратный слеш "\\\\" в путях!**

- **csv_read(fullpath:str, encoding:str='utf-8', fieldnames=None, delimiter:str=';', quotechar:str='"')->list** — прочитать CSV файл и вернуть содержимое в виде списка со словарями.
- **csv_write(fullpath:str, content:list, fieldnames:tuple=None, encoding:str='utf-8', delimiter:str=';', quotechar:str='"', quoting:int=csv.QUOTE_MINIMAL)->str** — записывает список словарей как CSV файл. Если *fieldnames* не указан - берёт ключи первого словаря в качестве заголовков. Возвращает полный путь к файлу. Пример *content*:

		[
			{'name': 'some name',
			'number': 1}
			, {'name': 'another name',
			'number': 2}
			...	
		]
- **dir_copy(fullpath:str, destination:str)->int** — копировать папку и всё её содержимое. Возвращает количество ошибок при копировании.
- **dir_delete(fullpath:str)** — удалить папку.
- **dir_dialog(title:str=None, default_dir:str='', on_top:bool=True, must_exist:bool=True)->str** — диалог выбора папки.
- **dir_dirs(fullpath, subdirs:bool=True)->list** — возвращает список полных путей всех каталогов в данном каталоге и его подкаталогах.
- **dir_exists(fullpath:str)->bool** — папка существует?
- **dir_files(fullpath, subdirs:bool=True, \*\*rules)->Iterator[str]** — возвращает список полных путей всех файлов в указанной папке и её подпапках.
	*subdirs* - включая файлы из вложенных папок.  
	*rules* - правила для функции `path_rule`  

		tass( tuple(dir_files('plugins', in_ext='jpg') ), tuple() )
		tass(
			tuple(dir_files('plugins', in_ext='py'))[0]
			, 'plugins\\constants.py'
		)
		tass(
			tuple( dir_files('plugins', ex_ext='pyc') )
			, tuple( dir_files('plugins', in_ext='py') )
		)

- **dir_find(fullpath, only_files:bool=False)->list** — возвращает список путей в указанной папке.

	*fullpath* передается в **glob.glob**

	*only_files* - возвращать только файлы, а не файлы и каталоги.

	Примеры:
		
		# Только файлы в текущем каталоге:
		dir_find('d:\\folder\\*.jpg')

		# с подкаталогами:
		dir_find('d:\\folder\\**\\*.jpg')

- **dir_junc(src_path, dst_path)** — создает *junction* ссылку на каталог.  
	Только для локальных путей.  

		td = dir_test()
		tdj = file_name_add(td, ' junc')
		dir_junc(td, tdj)
		asrt( dir_exists(tdj), True )
		# Удалить исходный каталог:
		dir_delete(td)
		# Теперь ссылка не работает:
		asrt( dir_exists(tdj), False )
		dir_delete(tdj)

- **dir_list(fullpath, \*\*rules)->Iterator[str]** — возвращает все содержимое каталога (файлы и папки).  
	*rules* - правила для функции `path_rule`  

		tass( 'resources\\icon.png' in dir_list('resources'), True)
		tass( 'resources\\icon.png' in dir_list('resources', ex_ext='png'), False)
		tass(
			benchmark(lambda d: tuple(dir_list(d)), 'log', b_iter=5)
			, 500_000
			, '<'
		)

- **dir_purge(fullpath, days:int=0, subdirs:bool=False, creation:bool=False, test:bool=False, print_del:bool=False, \*\*rules)->int** — удаляет файлы старше *x* дней.  
	Возвращает количество удаленных файлов и папок.
	
	*days=0* - удалить всё  
	*creation* - использовать дату создания, в противном случае использовать дату последней модификации.  
	*subdirs* - удалять и во вложенных папках. Пустые вложенные папки будут удалены.  
	*test* - только вывести те файлы и папки, которые следует удалить, без фактического удаления.  
	*print_del* - вывести путь при удалении.  
	*rules* - правила для функции `path_rule`  

- **dir_rnd_dirs(fullpath, attempts:int=5, filter_func=None)->str** — то же самое, что и `dir_rnd_file`, но возвращает подкаталоги.
- **dir_rnd_files(fullpath, file_num:int=1, attempts:int=5, \*\*rules)->Iterator[str]** — получает случайные файлы из каталога или None, если ничего не найдено.  
	*file_num* - сколько файлов нужно вернуть.  
	*rules* - кортеж правил из `path_rule`.

	Предназначена для больших каталогов, перечисление которых занимает много времени.  
	Функция не будет возвращать один и тот же файл дважды.  
	Пример:

		dir_rnd_files('.')
		tuple(dir_rnd_files('.', ex_ext='py'))
	
	По сравнению с `dir_files` с `random.choice`:

		> benchmark(lambda: random.choice( list(dir_files(temp_dir() ) ) ), b_iter=10)
		benchmark: 113 367 113 ns/loop

		> benchmark(dir_rnd_files, a=(temp_dir(), ), b_iter=10)
		620

		> len( tuple( dir_files( temp_dir() ) ) )
		1914

- **dir_size(fullpath:str, unit:str='b')->int** — размер папки в указанных единицах.
- **dir_sync(src_dir, dst_dir, report:bool=False, \*\*rules)->dict** — синхронизировать два каталога.  
	*rules* смотреть в `path_rule`.  
	Возвращает словарь с ошибками:  
	
		{'path\\file.exe': 'copy error', ...}

	
- **dir_zip(source:str, destination:str)->str** — упаковать папку в архив и вернуть путь к архиву.
- **dir_user_desktop()->str** — папка *рабочего стола* текущего пользователя.
- **dir_user_startup()->str** — папка *автозагрузки* текущего пользователя.
- **drive_io(drive_num:int=None)->dict** — возвращает генератор счетчиков физического диска (не раздела!) который возвращает именованные кортежи со счетчиками. пример:

		dio = drive_io()
		print(next(dio)[0].read_bytes)
		time_sleep('1 sec')
		print(
			file_size_str(next(dio)[0].total_bytes_delta)
		)
		
- **drive_list(exclude:str='')->str** — строка с буквами логических дисков.
- **file_append(fullpath:str, content:str)->str** — дописывает *content* к файлу. Создаёт файл, если он не существует. Возвращает полное имя файла.
- **file_attr_set(fullpath, attribute:int=win32con.FILE_ATTRIBUTE_NORMAL)** — изменение атрибутов файла.
- **file_backup(fullpath:str, dest_dir:str='', suffix_format:str='_%y-%m-%d_%H-%M-%S')->str** — копировать 'somefile.txt' в 'somefile_2019-05-19_21-23-02.txt'. *dest_dir* - папка назначения. Если не указана - текущая папка файла. Возвращает полное имя нового файла.
- **file_basename(fullpath:str)->str** — возвращает *базовое* имя файла - без папки и расширения.
- **file_backup(fullpath, folder:str=None)** — сделать копию файла, дописав в имя текущую дату и время.
	*folder* — папка, куда следует поместить копию. Если не указано — поместить в папке оригинального файла.
- **file_copy(fullpath, destination:str, copy_metadata:bool=False)** — копировать файл. *destination* может быть папкой или полным путём к копии файла.
- **file_date_a(fullpath)** — дата открытия файла.
- **file_date_c(fullpath)** — дата создания файла.
- **file_date_m(fullpath)** — дата изменения файла.
- **file_date_set(fullpath, datec=None, datea=None, datem=None)** — устанавливает дату файла.  

		fp = temp_file(content=' ')
		asrt(
			benchmark(file_date_set, ka={'fullpath': fp, 'datec': time_now()}, b_iter=3)
			, 220000
			, "<"
		)
		file_delete(fp)

- **file_delete(fullpath:str)** — удалить файл. Смотрите так же *file_recycle*.
- **file_dialog(title:str=None, multiple:bool=False, default_dir:str='', default_file:str='', wildcard:str='', on_top:bool=True)** — открывает стандартный диалог выбора файла. Возвращает полный путь или список полных путей, если _multiple_ == True.
- **file_dir(fullpath:str)->str:** — получить полное имя папки, в которой файл лежит.
- **file_dir_repl(fullpath, new_dir:str)->str** — изменяет каталог файла (в полном пути)
- **file_drive(fullpath)->str** — возвращает букву диска в нижнем регистре из имени файла:

		assert file_drive(r'c:\\pagefile.sys') == 'c'

- **file_exists(fullpath:str)->bool** — файл существует?
- **file_ext(fullpath:str)->str** — расширение файла без точки.
- **file_hash(fullpath:str, algorithm:str='crc32')->str**: - возвращает хэш файла. *algorithm* - 'crc32' или любой алгоритм из hashlib ('md5', 'sha512' и т.д.)
- **file_log(fullpath:str, message:str, encoding:str='utf-8', time_format:str='%Y.%m.%d %H:%M:%S')** — записать *message* в файл *fullpath*.
**file_lock_wait(fullpath, wait_interval:str='100 ms')->bool** — блокирует выполнение до тех пор, пока файл не станет доступен. Использование - подождать, пока другой процесс не прекратит запись в файл.
- **file_move(fullpath:str, destination:str)** — переместить файл.
- **file_name(fullpath:str)->str** — получить имя файла без папки.
- **file_name_add(fullpath, suffix:str='', prefix:str='')->str** — добавляет строку (префикс или суффикс) к файлу перед расширением. Пример: 
	
		file_name_add('my_file.txt', suffix='_1')
		'my_file_1.txt'

- **file_name_fix(filename:str, repl_char:str='\_')->str** — заменяет запрещённые символы на _repl_char_. Удаляет пробелы в начале и в конце. Добавляет '\\\\?\\' к длинным путям.
- **file_name_rem(fullpath, suffix:str='', prefix:str='')->str** — удаляет суффикс или префикс из имени файла.
- **file_print(fullpath, printer:str=None, use_alternative:bool=False)->bool** — распечатывает файл на указанном принтере.
- **file_read(fullpath:str)->str:** — получить содержимое файла.
- **file_recycle(fullpath:str, silent:bool=True)->bool** — переместить файл в корзину. *silent* - не показывать стандартный системный диалог подтверждения удаления в корзину. Возвращает True в случае успешного удаления.
- **file_relpath(fullpath, start)->str** — относительное имя файла.
- **file_rename(fullpath:str, dest:str)->str** — переименовать файл. *dest* — полный путь или просто новое имя файла без папки.
- **file_size(fullpath:str, unit:str='b')->bool:** — получить размер файла (gb, mb, kb, b).
- **file_write(fullpath:str, content=str, encoding:str='utf-8')->str** — сохраняет *content* в файл. Создаёт файл, если он не существует. Если fullpath = '' или None, используется temp_file(). Возвращает полное имя файла.
- **file_zip(fullpath, destination:str)->str** — сжать файл или файлы в архив.
	*fullpath* — строка с полным именем файла или список с файлами.
	*destiniation* — полный путь к архиву.
- **drive_free(letter:str, unit:str='GB')->int:** — размер свободного места на диске (gb, mb, kb, b).
- **is_directory(fullpath:str)->bool:** — указанный путь является папкой?
- **path_exists(fullpath:str)->bool:** — указанный путь существует (не важно файл это или папка)?
- **path_short(fullpath, max_len:int=100)->str** — сокращает длинное имя файла для отображения.

		path = r'c:\Windows\System32\msiexec.exe'
		tass(path_short(path, 22), 'c:\Windo...msiexec.exe')
		tass(path_short(path, 23), 'c:\Window...msiexec.exe')

- **rec_bin_purge(drive:str=None, progress:bool=False, sound:bool=True)** — очищает корзину.

		# One drive:
		rec_bin_purge('c')
		# All drives:
		rec_bin_purge()

- **rec_bin_size(drive:str|None=None)->tuple** — получает общий размер и количество элементов в корзине для указанного диска.  
- **shortcut_create(fullpath, dest:str=None, descr:str=None, icon_fullpath:str=None, icon_index:int=None, win_style:int=win32con.SW_SHOWNORMAL, cwd:str=None)->str** — создаёт ярлык для файла. Возвращает полный путь к файлу ярлыка.
	- dest - полное имя файла ярлыка. Если не указано, используется папка рабочего стола текущего пользователя.
	- descr - описание
	- icon_fullpath - файл-источник для иконки.
	- icon_index - номер иконки в файле. Если *icon_fullpath* не указан, используется *fullpath*.

- **temp_dir(new_dir:str=None)->str** — возвращает путь ко временной папке. Если указана *new_dir* - создаёт подпапку во временной папке и возвращает её путь.
- **temp_file(prefix:str='', suffix:str='')->str** — возвращает имя для временного файла.

### Сеть

- **domain_ip(domain:str)->list** — получить список IP-адресов по имени домена.
- **file_download(url:str, destination:str=None)->str:** — скачать файл и вернуть полный путь.
	*destination* — может быть *None*, полным путём к файлу или папкой. Если *None*, то скачать во временную папку и вернуть полное имя.
- **ftp_upload(fullpath, server:str, user:str, pwd:str, dst_dir:str='/', port:int=21, active:bool=True, debug_lvl:int=0, attempts:int=3, timeout:int=10, secure:bool=False, encoding:str='utf-8')->tuple** — загружает файл(ы) на FTP-сервер. Возвращает (True, None) или (False, ('error1', 'error2'...)).
  
	*debug_lvl* - установите в 1, чтобы увидеть команды.

- **html_element(url:str, element, element_num:int=0)->str:** — получить текст HTML-элемента по указанной ссылке.
	*element* — словарь, который содержит информацию о нужном элементе (его имя, атрибуты); или список таких словарей; или строка с xpath.
	*element_num* - номер элемента, если таких находится несколько.
	Пример со словарём:

		# Получить внутренний текст элемента span, у которого есть
		# атрибут itemprop="softwareVersion"
		element={
			'name': 'span'
			, 'attrs': {'itemprop':'softwareVersion'}
		}
	
	Посмотрите на задачу *get_current_ip* в [Примеры задач](#task-examples)

- **html_clean(html_str:str, separator=' ')->str** — очищает строку от HTML тэгов.
- **is_online(\*sites, timeout:float=2.0)->int** — проверяет наличие интернет-соединения, используя *HEAD* запросы к указанным веб-сайтам.  
	Функция не вызовет исключения.  
	*timeout* - тайм-аут в секундах.  

		tass( is_online(), 2 )
		tass( is_online('https://non.existent.domain'), 0 )

- **json_element(url:str, element:list)** — аналог **html_element** для JSON.
	*element* — список с картой для нахождения нужного элемента в структуре json.
	Пример: *element=['usd', 2, 'value']*
- **http_req(url:str, encoding:str='utf-8', post_file:str=None, post_hash:bool=False)->str:** — скачать указанную страницу и вернуть её содержимое. *post_file* - отправить указанный файл POST запросом. *post_hash* - в запросе указать хэш файла для проверки целостности (смотрите [Свойства задачи](#свойства-задачи)).
- **http_req_status(url:str, method='HEAD')->int** — возвращает статус HTTP-запроса:

		assert http_req_status('https://github.com') == 200
	
- **net_html_unescape(html_str:str)->str** — декодирует экранированные символы (HTML):
		
		"That&#039;s an example" -> "That's an example"

- **net_pc_ip()->str** — возвращает IP-адрес компьютера.
- **net_url_decode(url:str, encoding:str='utf-8')->str** — декодирует URL.
- **net_url_encode(url:str, encoding:str='utf-8')->str** — кодирует URL.
- **pc_name()->str** — имя компьютера.
- **ping_icmp(host:str, count:int=3, timeout:int=500, encoding:str='cp866')->tuple** — возвращает (True, (% потерь, среднее время) ) или (False, 'текст ошибки'). Примеры:
	
		ping_icmp('8.8.8.8')
		> (True, (0, 47))
		ping_icmp('domain.does.not.exist')
		> (False, 'host unreachable (1)')

- **ping_tcp(host:str, port:int, count:int=1, pause:int=100, timeout:int=500)->tuple** — измерение потерь и времени отклика при tcp-соединении. Возвращает (True, (% потерь, время в мс) ) или (False, 'текст ошибки').
	
	*pause* - пауза в миллисекундах между попытками 
	
	*timeout* - время ожидания ответа в миллисекундах

	Примеры:

		ping_tcp('8.8.8.8', 443)
		> (true, (0, 49))
		ping_tcp('domain.does.not.exist', 80)
		> (false, '[errno 11004] getaddrinfo failed')

- **table_html(table:list, headers:bool=True , empty_str:str='-', consider_empty:tuple=(None, '') , table_class:str='')->str** — преобразует список кортежей в HTML таблицу. Пример списка:

		[
			('name', 'age'),
			('john', '27'),
			('jane', '24'),
		]

- **url_hostname(url:str, , sld:bool=True)->str** — извлечь имя домена из URL.

	*sld* - если True, то вернуть домен второго уровня, иначе вернуть полный.

		assert url_hostname('https://www.example.gov.uk') == 'example.gov.uk'
		assert url_hostname('https://www.example.gov.uk', sld=False) \
		== 'www.example.gov.uk'
		assert url_hostname('http://user:pwd@abc.example.com:443/api') \
		== 'example.com'
		assert url_hostname('http://user:pwd@abc.example.com:443/api'
		, sld=False) == 'abc.example.com'
		assert url_hostname('http://user:pwd@192.168.0.1:80/api') \
		== '192.168.0.1'

- **xml_element(url:str, element:str, element_num:int=0, encoding:str='utf-8', \*\*kwargs)** — скачивает документ по ссылке и возвращает значение по указанному XPath. Например:

	element='/result/array/msgContact[1]/msgCtnt'


### Система

В функциях для работы с окнами аргумент *window* может быть или строкой с заголовком окна или числом, представляющим handle окна.

- **free_ram(unit:str='percent')** — количество свободной памяти. *unit* — 'kb', 'mb'... или 'percent'.
- **idle_duration(unit:str='msec')->int** — сколько прошло времени с последней активности пользователя.
- **monitor_off()** — выключает монитор.
- **monitor_on()** — включает монитор.
- **registry_get(fullpath:str)** — получить значение ключа из реестра Windows.
	*fullpath* — строка вида 'HKEY_CURRENT_USER\\\Software\\\Microsoft\\\Calc\\\layout'
- **win_activate(window=None)->int** — вывести указанное окно на передний план. *window* может строкой с заголовком или числовым хэндлом нужного окна.
	Примечание: не всегда возможно активировать окно. Оно будет просто мигать на панели задач.  
- **win_by_pid(process)->tuple** — возвращает главное окно процесса в виде кортежа `(hwnd:int, title:str)`.
- **win_close(window=None, wait:bool=True)->bool** — закрывает окно и возвращает True при успехе.
- **win_find(title:str)->list** — вернуть список хэндлов окон, с указанным заголовком.
- **win_hide(window=None)->int** — скрыть окно.
- **win_is_min(window)->bool|None** — возвращает `True`, если окно свернуто.

		asrt( win_is_min(win_get(class_name=WIN_TASKBAR_CLS)), False )

- **win_list(title_filter:str=None, class_filter:str=None, case_sensitive:bool=False)->list** — список заголовков всех окон. *title_filter* - вернуть только заголовки с этой подстрокой.
**- win_on_top(window=None, on_top:bool=True)->int** — делает указанное окно поверх других окон.
- **win_show(window=None)->int** — показать окно.
- **win_title_set(window=None, new_title:str='')->int** —  найти окно по заголовку *cur_title* и поменять на *new_title*.

### Почта

- **mail_check(server:str, login:str, password:str, folders:list=['inbox'], msg_status:str='UNSEEN', headers:tuple=('subject', 'from', 'to', 'date'), silent:bool=True)->Tuple[ List[MailMsg], List[str] ]** — возвращает список объектов MailMsg и список ошибок.  
	*headers* - заголовки сообщений для получения. Вы можете получить к ним доступ позже в атрибутах MailMsg.  

- **mail_download(server:str, login:str, password:str, output_dir:str, folders:list=['inbox'], trash_folder:str='Trash')->tuple** — скачивает все письма в указанную папку. Успешно скачанные письма перемещаются в IMAP *trash_folder* папку на сервере. Возвращает кортеж из двух списков: список с декодированными заголовками писем и список с ошибками.
- **mail_send(recipient:str, subject:str, message:str, smtp_server:str, smtp_port:int, smtp_user:str, smtp_password:str)** — отправить письмо. Поддерживает отправку с русским заголовком и русским текстом.

### Процессы

- **proc_start(proc_path:str, args:str, wait:bool=False)** — запустить приложение. Если *wait=True* — возвращает код возврата, а если *False*, то возвращает PID созданного процесса.
	*proc_path* — полный путь к исполняемому файлу.
	*args* — аргументы командной строки.
	*wait* — приостановить выполнение задачи, пока не завершится запущенный процесс.
- **file_open(fullpath:str)** — открыть файл или URL в приложении по умолчанию.
- **proc_close(process, timeout:int=10, cmd_filter:str=None)** — мягкое завершение процесса: сначала закрываются все окна, принадлежащие указанному процессу, а по истечении таймаута (в секундах) убивается сам процесс, если ещё существует. *cmd_filter* - убивать только процессы, содержащие эту строку в командной строке.
- **proc_exists(process, cmd_filter:str=None, user_filter:str=None)->int** — проверяет, существует ли процесс и возвращает PID.
	*process* - имя файла или PID.  
	*cmd_filter* - необязательная строка для поиска в	командной строке процесса.  
	*user_filter* - поиск только в процессах	указанного пользователя. Формат: pc\\username  
- **proc_list(name:str='', cmd_filter:str=None)->list —** получить список процессов. Список содержит объекты *DictToObj*, у которых есть следующие свойства:
	*pid* — числовой идентификатор.
	*name* — имя файла.
	*username* — имя пользователя.
	*exe* — полный путь к файлу.
	*cmdline* — комндная строка в виде списка.

	*cmd_filter* - фильтруем по наличию этой строки в командной строке.

	Пример — распечатать PID всех процессов Firefox:

		for proc in proc_list('firefox.exe'):
			print(proc.pid)

- **proc_cpu(process, interval:float=1.0)->float** — возвращает использование ЦП указанного PID за указанный интервал времени в секундах.  
	Если процесс не найден, то возвращается -1:

		tass(proc_cpu('not existing process'), -1)
		tass(proc_cpu(0), 1, '>')
		
- **proc_kill(process, cmd_filter:str=None)** — убить указанный процесс. *process* может быть строкой с именем исполняемого файла, тогда будут завершены все процессы с таким названием, либо это может быть числовой PID, и тогда будет завершён только указанный процесс. *cmd_filter* - убивать только процессы, содержащие эту строку в командной строке.
- **proc_uptime(process)->float** — возвращает время работы процесса в секундах или -1.0, если процесс не найден.
- **screen_width()->int** — ширина экрана.
- **screen_height()->int** — высота экрана.
- **service_start(service:str, args:tuple=None)** — запускает службу.
- **service_stop(service:str)->tuple** — останавливает службу.
- **service_running(service:str)->bool** — служба запущена?
- **wts_message(sessionid:int, msg:str, title:str, style:int=0, timeout:int=0, wait:bool=False)->int** — отправляет сообщение терминальной сессии. *style* - стили как в msgbox (0 - MB_OK). *timeout* - таймаут в секундах (0 - без таймаута). Возвращает то же, что и msgbox.
- **wts_cur_sessionid()->int** — возвращает SessionID текущего процесса.
- **wts_logoff(sessionid:int, wait:bool=False)->int** — завершает терминальную сессию. *wait* - ждать завершения работы.
- **wts_proc_list(process:str=None)->list** — возвращает список объектов *DictToObj* с такими свойствами: *.sessionid:int*, *.pid:int*, *.process:str* (имя исполняемого файла), *.pysid:obj*, *.username:str*, *.cmdline:list*. *process* - фильтровать выдачу по имени процесса.
- **wts_user_sessionid(users, only_active:bool=True)->list** — преобразует список пользователей в список Session ID. *only_active* - вернуть только  WTSActive сессии.

### Шифрование

- **file_enc_write(fullpath:str, content:str, password:str, encoding:str='utf-8')**: — зашифровывает *content* и записывает в файл. Соль добавляется в виде расширения файла. Возвращает статус и полный путь/ошибку.
- **file_enc_read(fullpath:str, password:str, encoding:str='utf-8')->tuple**: — расшифровывает содержимое файла. Возвращает статус и содержимое/ошибку.
- **file_encrypt(fullpath:str, password:str)->tuple** — зашифровывает файл. Добавляет соль в виде расширения. Возвращает статус, полный путь/ошибку.
- **file_decrypt(fullpath:str, password:str)->tuple** — расшифровывает файл, возвращает статус и полный путь/ошибку.

### Mikrotik RouterOS

- **routeros_query(query:list, device_ip:str=None, device_port:str='8728', device_user:str='admin', device_pwd:str='')** — послать запрос на указанный маршрутизатор и вернуть результат. Запросы в API имеют специфический синтаксис, отличающийся от комманд для терминала, так что смотрите в [wiki](https://wiki.mikrotik.com/wiki/Manual:API).
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

- **routeros_send(cmd:str, device_ip:str=None, device_port:str='8728', device_user:str='admin', device_pwd:str='')** — отправить команду на указанный маршрутизатор и получить статус выполнения и ошибку, если есть.
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
	
- **routeros_find_send(cmd_find:list, cmd_send:list, device_ip:str=None, device_port:str='8728', device_user:str='admin', device_pwd:str='')** — комбинированное слово для операций, требующих предварительного поиска номеров (*find* в терминале)
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


## Полезные советы

### Переменные

Если вы хотите сохранить что-нибудь так, чтобы оно пережило перезагрузку кронтаба, используйте глобальный словарь **gdic**:

	def demo__gdic():
		if not gdic.get('test var'):
			gdic['test var'] = 0
		gdic['test var'] += 1
		dialog(f'Попробуйте перечитать кронтаб: {gdic["test var"]}')

Если вы хотите сохранить что-нибудь, чтобы это пережило перезапуск Taskopy, то используйте файловые переменные: функции **var_get**, **var_set** и т.д.

### Развертывание и надежность

**Как обновлять код задачи на нескольких компьютерах.**  
Вы можете определить задачу не только в *crontab*, но и в расширении, используя декоратор *task_add*. Таким образом, на клиентском компьютере, вы можете импортировать из расширения один раз в *crontab*, а затем обновлять только файл с расширением, в котором содержится задача.

Вы можете программно перезагружать кронтаб с помощью **crontab_reload**. Это безопасно, т.к. на самом деле кронтаб сначала загружается в тестовом режиме. Даже если в кронтабе будут грубые ошибки, обновленный кронтаб не загрузится, и старые задачи будiут по-прежнему выполняться.

Все исключения обрабатываются и логируются. Вы можете скачивать логи с других компьютеров (<http://127.0.0.1:8275/log>) в JSON формате и искать исключения по слову *Traceback*

Приложение может работать неделями непрерывно без существенных утечек памяти, но это, конечно же, зависит от того, не допустил ли сам пользователь ошибок в задачах.

## Расширение для Firefox
https://addons.mozilla.org/ru/firefox/addon/send-to-taskopy/

Расширение просто добавляет пункт в контекстное меню. С помощью него можно запустить задачу из Taskopy.

В настройках расширения указываете URL вашей задачи, которая будет обрабатывать данные, например:

	http://127.0.0.1:8275/get_data_from_browser

У этой задачи должны быть указаны атрибуты _data_ и _http=True_. В атрибут *data* будут передана информация в формате *DataBrowserExt*.

Пример задачи для проигрывания Youtube видео в PotPlayer:

	def get_data_from_browser(data, http=True, menu=False, log=False):
		if ('youtube.com' in data.link_url
		or 'youtu.be' in data.link_url):
			proc_start(
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
- По идее давно уже нужен тестировщик :)
- Расскажите о Taskopy друзьям.

## Примеры задач
- Свободное место на дисках
- Текущий IP адрес
- Добавление IP-адреса в маршрутизатор MikroTik
- Проверка на Virustotal

Проверяем свободное место на всех дисках каждые полчаса:

	def check_free_space_demo(submenu='demo'
	, every='30 minutes'):
		for d in drive_list():
			if drive_free(d) < 10:
				dialog(f'Осталось мало места: {d}')

Показываем сообщение с текущим внешним IP-адресом с помощью сервиса dyndns.org:

	def get_current_ip_demo(submenu='demo'):
		# Получаем текст HTML-тэга 'body' со страницы checkip.dyndns.org
		# html_element вернёт строку вроде 'Current IP Address: 11.22.33.44'
		ip = html_element(
			'http://checkip.dyndns.org/'
			, {'name': 'body'}
		).split(': ')[1]
		tprint(f'Текущий IP: {ip}')
		dialog(f'Текущий IP: {ip}', timeout=10)

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
		dialog('Готово!', timeout=5)

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
			dialog('Ошибка HTTP-запроса')
			return
		if scan_result['response_code'] == 0:
			dialog('Неизвестный файл', timeout=3)
			return
		res = DictToObj(scan_result)
		for av in res.scans.keys():
			if res.scans[av]['detected']:
				print(f'{av}: ' + res.scans[av]['result'])
		dialog(f'Результат: {res.positives} из {res.total}', timeout=5)

Получаем файл через HTTP POST запрос и выводим сообщение с комментарием и полным именем файла:

	def http_post_demo(data, http=True, log=False, menu=False):
		dialog(f'{data.filecomment}\n\n{data.post_file}')

Пример отправки запроса в задачу:

	curl -F "filecomment=Take this!" -F "file=@d:\my_picture.jpg" http://127.0.0.1:8275/http_post_demo
