
### Планировщик для Windows на основе Python с горячими клавишами, меню в трее, HTTP-сервером и многим другим.

<p align="center">
	<img src="https://i6.imageban.ru/out/2019/07/04/a6f6538a80bc7a62ab06ce5cea295a93.png">
</p>

Исходный код: [https://github.com/vikilpet/Taskopy](https://github.com/vikilpet/Taskopy)

Привязать ваш код к горячей клавише или HTTP-запросу:
```python
def my_task(hotkey='ctrl+shift+t', http=True):
	print('Это моя задача!')
```
Теперь можно нажать Ctrl+Shift+T или открыть в браузере http://127.0.0.1/task?my_task и задача будет выполнена.

Другой пример: показываем сообщение каждый день в 10:30 и скрываем из меню:
```python
def my_another_task(schedule='every().day.at("10:30")', menu=False):
	msgbox('Прими таблетки', ui=MB_ICONEXCLAMATION)
```

## Содержание
- [Установка](#установка)
- [Использование](#использование)
- [Свойства задачи](#свойства-задачи)
- [Настройки](#настройки)
- [Ключевые слова](#ключевые-слова)
	- [Общие](#общие)
	- [Клавиатура](#клавиатура)
	- [Файлы и папки](#файлы-и-папки)
	- [Сеть](#сеть)
	- [Система](#система)
	- [Процессы](#процессы)
	- [Winamp](#winamp)
	- [Mikrotik RouterOS](#mikrotik-routeros)
- [Помочь проекту](#помощь-проекту)
- [Примеры задач](#примеры-задач)

## Установка
### Вариант 1: архив с исполняемым файлом.

**Требования:** Windows 7 и выше.
Вы можете [скачать](https://github.com/vikilpet/Taskopy/releases) zip архив (taskopy.zip), но многие не особо качественные антивирусы не любят Python, упакованный в exe, так что VirusTotal покажет примерно 7 срабатываний.

### Вариант 2: Python
**Требования:** Python 3.7+; Windows 7 и выше.

Скачайте проект, установите зависимости:
```
pip install -r requirements.txt
```	
Сделайте ярлык для taskopy.py и поместите в автозагрузку:
```
%userprofile%\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\
```
В свойствах ярлыка выберите запуск минимизированным а так же смените иконку на resources\\logo.ico

## Использование
Откройте _crontab.py_ в вашем любимом текстовом редакторе и создайте задачу как функцию с аргументами:
```python
def demo_task_3('left_click'=True, log=False):
	app_start('calc.exe')
```	
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
	```python
	schedule='every().hour'
	```
	Каждую среду в 13:15:
	```python
	schedule='every().wednesday.at("13:15")'
	```
	Можно запланировать сразу несколько раз через список (каждую среду в 18:00 и каждую пятницу в 17:00):
	```python
	schedule=['every().wednesday.at("18:00")', 'every().friday.at("17:00")']
	```
- **active** (True) — включить-выключить задачу.
- **startup** (False) — запускать при загрузке Taskopy.
- **sys_startup** (False) — запускать при загрузке Windows (время работы системы меньше 3 минут).
- **left_click** (False) — назначить на левый клик по иконке в трее.
- **log** (True) — логировать в консоль и в лог.
- **single** (True) — одновременно может выполняться только одна копия задачи.
- **submenu** (None) — разместить в подменю.
- **result** (False) — задача должна вернуть какое-то значение. Используется вместе с **http** опцией для выдачи результатов задачи.
- **http** (False) — запускать задачу через HTTP запрос. Синтаксис запроса: *http://127.0.0.1/task?имя_задачи* где «имя_задачи» это название функции-задачи из crontab.
	Если свойство **result** также включено, то HTTP-запрос покажет то, что вернула задача или 'OK' если ничего не было возвращено.
	Пример:
	```python	
	def demo_task_4(http=True, result=True):
		# Получить список файлов в папке Taskopy:
		listing = dir_list('*')
		# вернуть этот список как строку, разделённую br-тэгом.
		# wordpress съедает угловые скобки, поэтому здесь 'br' без них:
		return 'br'.join(listing)
	```
	Результат в браузере:
	backup
	crontab.py
	log
	resources
	settings.ini
	taskopy.exe
	```
	Смотрите в разделе [Настройки](#settings) про привязывание HTTP-сервера к IP и порту.
- **caller** — при указании в свойствах, в эту переменную будет записано, кто именно запустил задачу. Возможные варианты: http, menu, scheduler, hotkey. caller следует указывать перед другими свойствами задачи.
- **data** — для использования совместо с опцией **http**. Должен идти перед другими свойствами задачи. В эту переменную будут переданы данные из HTTP-запроса, так что с ними можно будет работать в тексте задачи, обращаясь как к свойству. Как минимум там будут содержаться:
	*data.client_ip* — IP-адрес того, кто выполнил запрос.
	*data.path* — весь относительный путь из URL, начиная с *task?*.
	Также в data будут содержаться стандартные HTTP-заголовки, такие как *User-Agent*, *Accept-Language* и т.д.
	Если в URL добавить какие-либо параметры согласно общепринятой схеме *param1=value1&param2=value2*, то они будут обработаны и также добавлены в data, таким образом вы можете обращаться к ним в теле задаче как *data.param1* и *data.param2*.
	Пример:
	```python
	def alert(data, http=True, single=False, menu=False):
		msgbox(
			data.text
			# Если есть, испльзовать data.title, иначе 'Alert'
			, title=data.title if data.title else 'Alert'
			, dis_timeout=1
		)
	```
	После этого набираем в браузере такой запрос:
	http://127.0.0.1/task?alert&text=MyMsg&title=MyTitle
	В результате чего будет выведено сообщение с заголовком *MyTitle* и текстом *MyMsg*.
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
- **white_list** (127.0.0.1) — список IP-адресов через запятую, от которых принимаются запросы.
- **server_port** (80) — порт HTTP-сервера.

## Ключевые слова
### Общие
- **msgbox(msg:str, title:str=APP_NAME, ui:int=None, wait:bool=True, timeout:int=None)->int** — показать сообщение и вернуть код нажатой кнопки.
	Аргументы:
	*msg* — сообщение
	*title* — заголовок
	*ui* — [опции показа](https://docs.microsoft.com/en-us/windows/desktop/api/winuser/nf-winuser-messagebox)
		Пример: _ui = MB_ICONINFORMATION + MB_YESNO_
	*wait* — если *False* — продолжить выполнение задачи, не дожидаясь закрытия сообщения.
	*timeout* (в секундах) — автоматически закрывать сообщение по истечении таймаута. Если сообщение закрыто по таймауту (пользователь не нажал никакую клавишу) и в _ui_ есть вариант с несколькими клавишами (например _MB_YESNO_) тогда сообщение вернёт 32000.
	*dis_timeout* (в секундах) — отключить кнопки на указанное количество секунд, чтобы было время подумать.
	Пример:
	```python
	def test_msgbox():
		if msgbox('Можно съесть пирожок?') == IDYES:
			print('Да!')
		else:
			print('Нельзя :-(')
	```
- **sound_play (fullpath:str, wait:bool)->str** — воспроизвести .wav файл. *wait* — ждать конца воспроизведения.
- **time_now(template:str='%Y-%m-%d\_%H-%M-%S')->str** — строка с текущей датой и временем.
- **pause(interval)** — приостановить выполнение задачи на указанное кол-во секунд. *interval* — время в секундах или строка с указанием единицы вроде '5 ms' или '6 sec' или '7 min'.
- **var_set(var_name:str, value:str)** — сохранить _значение_ переменной на диск. Таким образом можно хранить данные между запусками Taskopy.
- **var_get(var_name:str)->str** — получить значение переменной.
- **clip_set(txt:str)->** — поместить текст в буфер обмена.
- **clip_get()->str->** — получить текст из буфера обмена.
- **re_find(source:str, re_pattern:str, sort:bool=True)->list** — поиск в строке с помощью регулярного выражения. Возвращает список найденных значений.
- **re_replace(source:str, re_pattern:str, repl:str='')** — заменить в строке всё найденное с помощью регулярного выражения на _repl._
- **email_send(recipient:str, subject:str, message:str, smtp_server:str, smtp_port:int, smtp_user:str, smtp_password:str)** — отправить письмо. Поддерживает отправку с русским заголовком и русским текстом.
- **inputbox(message:str, title:str, is_pwd:bool=False)->str** — показать сообщение с вводом текста. Возвращает введённую строку или пустую строку, если пользователь нажал отмену.
	*is_pwd* — скрыть вводимый текст.
- **random_num(a, b)->int** — вернуть случайное целое число в диапазоне от a до b, включая a и b.
- **random_str(string_len:int=10, string_source:str=None)->str** — сгенерировать строку из случайных символов заданной длины.

### Клавиатура

**keys_pressed(hotkey:str)->bool** — нажата ли клавиша.
**keys_send(hotkey:str)** — нажать сочетание клавиш.
**keys_write(text:str)** — написать текст.

### Файлы и папки

**fullpath** означает полное имя файла, например 'c:\\\Windows\\\System32\\\calc.exe'

**ВАЖНО: всегда используйте двойной обратный слеш "\\\" в путях!**

- **csv_read(fullpath:str, encoding:str='utf-8', fieldnames=None, delimiter:str=';', quotechar:str='"')->list** — прочитать CSV файл и вернуть содержимое в виде списка со словарями.
- **dir_delete(fullpath:str):** — удалить папку.
- **dir_list(fullpath:str)->list:** — получить список файлов в папке.
	Примеры:
	- Получить список всех .log файлов в 'c:\\\Windows' **не учитывая** подпапки:
	```python
	dir_list('c:\\Windows\\*.log')
	```
	- Получить список всех .log файлов в 'c:\\\Windows' **включая** подпапки:
	```python
	dir_list('c:\\Windows\\**\\*.log')
	```
- **dir_zip(source:str, destination:str)->str** — упаковать папку в архив и вернуть путь к архиву.
- **file_backup(fullpath, folder:str=None):** — сделать копию файла, дописав в имя текущую дату и время.
	*folder* — папка, куда следует поместить копию. Если не указано — поместить в папке оригинального файла.
- **file_copy(fullpath:str, destination:str):** — копировать файл. *destination* может быть папкой или полным путём к копии файла.
- **file_delete(fullpath:str):** — удалить файл.
- **file_dir(fullpath:str)->str:** — получить полное имя папки, в которой файл лежит.
- **file_log(fullpath:str, message:str, encoding:str='utf-8', time_format:str='%Y.%m.%d %H:%M:%S')** — записать *message* в файл *fullpath*.
- **file_move(fullpath:str, destination:str):** — переместить файл.
- **file_name(fullpath:str)->str:** — получить имя файла без папки.
- **file_read(fullpath:str)->str:** — получить содержимое файла.
- **file_rename(fullpath:str, dest:str)->str** — переименовать файл. *dest* — полный путь или просто новое имя файла без папки.
- **file_size(fullpath:str, unit:str='b')->bool:** — получить размер файла (gb, mb, kb, b).
- **file_write(fullpath:str, content=str):** — записать текст в файл.
- **file_zip(fullpath, destination:str)->str** — сжать файл или файлы в архив.
	*fullpath* — строка с полным именем файла или список с файлами.
	*destiniation* — полный путь к архиву.
- **free_space(letter:str, unit:str='GB')->int:** — размер свободного места на диске (gb, mb, kb, b).
- **is_directory(fullpath:str)->bool:** — указанный путь является папкой?
- **path_exists(fullpath:str)->bool:** — указанный путь существует (не важно файл это или папка)?
- **purge_old(fullpath:str, days:int=0, recursive=False, creation:bool=False, test:bool=False):** — удалить файлы из папки старше указанного числа дней.
	Если *days* == 0 значит удалить вообще все файлы в папке.
	*creation* — использовать дату создания, иначе использовать дату последнего изменения.
	*recursive* — включая подпапки.
	*test* — не удалять на самом деле, а просто вывести в консоль список файлов, которые должны быть удалены.

### Сеть
- **domain_ip(domain:str)->list** — получить список IP-адресов по имени домена.
- **file_download(url:str, destination:str=None)->str:** — скачать файл и вернуть полный путь.
	*destination* — может быть *None*, полным путём к файлу или папкой. Если *None*, то скачать во временную папку и вернуть полное имя.
- **html_element_get(url:str, find_all_args)->str:** — получить текст HTML-элемента по указанной ссылке.
	*find_all_args* — словарь, который содержит информацию о нужном элементе (его имя, атрибуты). Пример:
	```python
	# Получить внутренний текст элемента span, у которого есть
	# атрибут itemprop="softwareVersion"
	find_all_args={
		'name': 'span'
		, 'attrs': {'itemprop':'softwareVersion'}
	}
	```
	Посмотрите на задачу *get_current_ip* в [Примеры задач](#task-examples)
- **is_online(*sites, timeout:int=2)->int:** — проверяет, есть ли доступ в Интернет, используя HEAD запросы к указанным сайтам. Если сайты не указаны, то использует google и yandex.
- **json_element(url:str, element:list):** — аналог **html_element** для json.
	*element* — список с картой для нахождения нужного элемента в структуре json.
	Пример: *element=['usd', 2, 'value']*
- **page_get(url:str, encoding:str='utf-8')->str:** — скачать указанную страницу и вернуть её содержимое.
- **url_hostname(url:str)->str** — извлечь имя домена из URL.

### Система
В функциях для работы с окнами аргумент *window* может быть или строкой с заголовком окна или числом, представляющим handle окна.

- **free_ram(unit:str='percent')** — количество свободной памяти. *unit* — 'kb', 'mb'... или 'percent'.
- **idle_duration(unit:str='msec')->int** — сколько прошло времени с последней активности пользователя.
- **monitor_off()** — выключить монитор.
- **registry_get(fullpath:str)** — получить значение ключа из реестра Windows.
	*fullpath* — строка вида 'HKEY_CURRENT_USER\\\Software\\\Microsoft\\\Calc\\\layout'
- **window_activate(window=None)->int** — вывести указанное окно на передний план. *window* может строкой с заголовком или числовым хэндлом нужного окна.
- **window_find(title:str)->list** — вернуть список хэндлов окон, с указанным заголовком.
- **window_hide(window=None)->int** — скрыть окно.
**- window_on_top(window=None, on_top:bool=True)->int** — делает указанное окно поверх других окон.
- **window_show(window=None)->int** — показать окно.
- **window_title_set(window=None, new_title:str='')->int** —  найти окно по заголовку *cur_title* и поменять на *new_title*.

### Процессы
- **app_start(app_path:str, app_args:str, wait:bool=False):** — запустить приложение. Если *wait=True* — возвращает код возврата, а если *False*, то возвращает PID созданного процесса.
	*app_path* — полный путь к исполняемому файлу.
	*app_args* — аргументы командной строки.
	*wait* — приостановить выполнение задачи, пока не завершится запущенный процесс.
- **file_open(fullpath:str):** — открыть файл или URL в приложении по умолчанию.
- **process_close(process, timeout:int=10)** — мягкое завершение процесса: сначала закрываются все окна, принадлежащие указанному процессу, а по истечении таймаута (в секундах) убивается сам процесс, если ещё существует.
- **process_exist(process, cmd:str=None)->bool** — проверяет, существует ли процесс и возвращает PID или False. *cmd* - необязательная строка для поиска в командной строке. Таким образом можно различать процессы с одинаковым исполняемым файлом но разной командной строкой.
- **process_list(name:str='')->list —** получить список процессов. Список содержит информацию объекты, у которых есть следующие свойства:
	*pid* — числовой идентификатор.
	*name* — имя файла.
	*username* — имя пользователя.
	*exe* — полный путь к файлу.
	*cmdline* — комндная строка в виде списка.
	Пример — распечатать PID всех процессов Firefox:
	```python
	for proc in process_list('firefox.exe'):
		print(proc.pid)
	```
- **process_cpu(pid:int, interval:int=1)->float** — процент загрузки процессора указанным PID. *interval* — время замера в секундах.
- **process_kill(process)** — убить указанный процесс. *process* может быть строкой с именем исполняемого файла, тогда будут завершены все процессы с таким названием, либо это может быть числовой PID, и тогда будет завершён только указанный процесс.

### Winamp
- **winamp_close** — закрыть Винамп.
- **winamp_fast_forward** — перемотка на 5 секунд вперёд.
- **winamp_fast_rewind** — перемотка на 5 секунд назад.
- **winamp_notification():** — показать уведомление (только для скина «Modern»).
- **winamp_pause():** — пауза.
- **winamp_play():** — воспроизведение.
- **winamp_status()->str:** — статус воспроизведения ('playing', 'paused' или 'stopped').
- **winamp_stop():** — остановить.
- **winamp_toggle_always_on_top** — установить/снять окно поверх всех окон.
- **winamp_toggle_main_window** — показать/скрыть окно Винампа.
- **winamp_toggle_media_library** — показать/скрыть окно библиотеки.
- **winamp_track_info(sep:str='   ')->str:** — получить строку с частотой, битрейтом и количеством каналов у текущего трека. *sep* — разделитель.
- **winamp_track_length()->str:** — длина трека.
- **winamp_track_title(clean:bool=True)->str:** — название текущего трека.

### Mikrotik RouterOS
- **routeros_query(query:list, device_ip:str=None, device_port:str='8728', device_user:str='admin', device_pwd:str='')** — послать запрос на указанный маршрутизатор и вернуть результат. Запросы в API имеют специфический синтаксис, отличающийся от комманд для терминала, так что смотрите в [wiki](https://wiki.mikrotik.com/wiki/Manual:API).
	Пример — получить информацию об интерфейсе bridge1:
	```python
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
	```
	Содержимое *data*:
	```
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
	```
- **routeros_send(cmd:str, device_ip:str=None, device_port:str='8728', device_user:str='admin', device_pwd:str='')** — отправить команду на указанный маршрутизатор и получить статус выполнения и ошибку, если есть.
	Пример: сначала получаем список постоянных («dynamic=false») записей в списке адресов «my_list», а затем удаляем все найденные записи:
	```python
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
	```
- **routeros_find_send(cmd_find:list, cmd_send:list, device_ip:str=None, device_port:str='8728', device_user:str='admin', device_pwd:str='')** — комбинированное слово для операций, требующих предварительного поиска номеров (*find* в терминале)
	*cmd_find* — список с командами для поиска значений.
	*cmd_send* — команда, которая будет выполняться для найденных элементов.
	Пример — удаление всех статических адресов из address-list:
	```python
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
	```		

## Помощь проекту
- [Мой вопрос на StackOverflow про показ меню по горячей клавише.](https://stackoverflow.com/questions/56079269/wxpython-popupmenu-by-global-hotkey) Если у вас есть знакомый эксперт по wxPython, пришлите ему эту ссылку, или добавьте награду, если ваш рейтинг позволяет.
- Расскажите о Taskopy друзьям.

## Примеры задач
```python
# Запуск iPython и копирование всех плагинов в буфер обмена
# , чтобы быстро вставить и получить доступ ко всем ключевым словам:
def iPython(submenu='WIP'):
	# Убиваем существующий процесс, если есть:
	process_kill('ipython.exe')
	# запускаем новый процесс:
	app_start('ipython')
	# получаем список всех .py файлов в папке 'plugins':
	plugs = dir_list('plugins\\*.py')
	plugs[:] = [
		'from ' + pl[:-3].replace('\\', '.')
		+ ' import *' for pl in plugs
	]
	# даём процессу время загрузиться:
	time_sleep(1.5)
	# вводим импорты из плагинов:
	keys_write(
		r'%load_ext autoreload' + '\n'
		+ r'%autoreload 2' + '\n'
		+ '\n'.join(plugs)
	)
	time_sleep(0.2)
	# отправляем control + enter, чтобы завершить ввод:
	keys_send('ctrl+enter')


# Проверяем свободное место на всех дисках (c, d, e).
# Добавляем слово 'caller' к опциям задачи, чтобы в самой задаче
# можно было проверить, каким способом она была вызвана.
# Планируем выполнение случайный интервал между 30 и 45 минутами:
def check_free_space(caller, schedule='every(30).to(45).minutes'):
	# Если задача была запущена через меню, показываем сообщение:
	if caller == 'menu':
		msg = (
			'Свободное место в ГБ:\n'
			+ f'c: {free_space("c")}\n'
			+ f'd: {free_space("d")}\n'
			+ f'e: {free_space("e")}\n'
		)
		# сообщение будет автоматически закрыто через 3 секунды:
		msgbox(msg, timeout=3)
	else:
		# Раз не из меню, значит запущена через планировщик.
		# Проверяем свободное место на дисках c, d, e и выводим
		# сообщение, если осталось меньше 3 ГБ:
		for l in 'cde':
			if free_space(l) < 3:
				msgbox(f'Осталось мало места: {l.upper()}')

# Показываем сообщение с текущим внешним IP-адресом:
def get_current_ip():
	# Получаем текст HTML-тэга 'body' со страницы checkip.dyndns.org
	# html_element_get вернёт строку вроде 'Current IP Address: 11.22.33.44'
	ip = html_element_get(
		'http://checkip.dyndns.org/'
		, {'name':'body'}
	).split(': ')[1]
	print(f'Текущий IP: {ip}')
	msgbox(f'Текущий IP: {ip}', timeout=10)

# Добавить IP-адрес из буфера обмена в список адресов
# маршрутизатора MikroTik:
def add_ip_to_list():
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
    msgbox('Done!', timeout=5)

# Запускаем калькулятор и меняем его заголовок на курс продажи
# доллара в Сбербанке. Назначаем выполнение задачи на клик
# левой клавишей мыши по иконке:
def demo_task_4(left_click=True):
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

# Проверяем статус посылок на Почте России
# Планируем выполнение случайный интервал между 120 и 150 минутами: 
def Проверить_статус_посылок(schedule='every(120).to(150).minutes'):
	# Список, который состоит из кортежей (списков), внутни
	# который сначала идёт номер для отслеживания, а потом
	# название посылки, чтобы понятно было.
	parcels = [
		('LL123456789CN', 'Сяоми')
		, ('RR123456789JP', 'Часы')
	]
	# Пустая строка, куда мы будем дописывать изменения статуса:
	msg = ''
	for tracking, name in parcels:
		# внутри цикла в tracking у нас оказался номер, а внутри
		# name - имя посылки
		# Получаем текущий (новый) статус:
		new_status = tracking_status_rp(tracking)
		# Если есть имя, то составляем имя по шаблону
		# название (номер для отслеживания)
		if name:
			parcel_name = f'{name} ({tracking})'
		else:
			parcel_name = tracking
		# Получаем предыдущий статус из "долговременного"
		# хранения:
		old_status = var_get('tracking_' + tracking)
		if old_status != new_status:
			# Статусы не совпадают, добавляем выводим в консоль
			print(f'Новый статус: «{parcel_name}» - {new_status}')
			# и сохраняем новый статус:
			var_set('tracking_' + tracking, new_status)
			# и добавляем к строке msg:
			msg += (
				f'«{parcel_name}»\n'
				+ f'	Было: {old_status}\n'
				+ f'	Стало: {new_status}\n'
			)
		else:
			# статус не изменился, просто выводим в консоль:
			print(f'Статус не изменился: «{parcel_name}» - {new_status}')
	# Если строка не пустая, показываем сообщение:
	if msg:
		msgbox(
			msg
			, title='Посылки'
			, dis_timeout=1
		)
```