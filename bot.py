# -*- encoding: utf-8 -*-
import logging
import asyncio
import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram import Router
from aiogram.filters import Command, Filter
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode



from config import Config
from db import DatabaseWrapper, AccessToken, Community, Settings, KrutkaSettings

import sys
import requests
import datetime
import vk_api as vk
import threading as th
import concurrent.futures as futuress
import re
from itertools import zip_longest

message_start = '''
Бот запущен :)
Все команды можно посмотреть в меню бота!
'''


####################
#     FSM FORMS    #
####################


class GroupAddingForm(StatesGroup):
    askgroups = State()

class GroupDeletingForm(StatesGroup):
    askgroups = State()

class TokenAddingForm(StatesGroup):
    asktokens = State()

class TokenDeletingForm(StatesGroup):
    asktokens = State()

class KrutkaForm(StatesGroup):
    askposts = State()
    asklimits = State()

class SettingsForm(StatesGroup):
    asklimits = State()
    askkeywords = State()





####################
#  CUSTOM FILTERS  #
####################

class IsAdminFilter(Filter):
    def __init__(self, config):
        self.admins = config.admins

    async def __call__(self,message: types.message):
        print('triggering filter')
        user_id = message.from_user.id
        print(user_id)
        if user_id not in self.admins:
            await message.reply(':)')
            return False
        else:
            return True

class BotWrapper():
#####################
# STARTING THE BOT  #
#####################

    def __init__(self, Config):
        self.dp = Dispatcher()
        self.router = Router()
        self.dp.include_router(self.router)
        self.bot = Bot(token=Config.tgToken, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
        self.db = DatabaseWrapper(Config)
        self.settings = self.get_settings()
        self.dummy_settings = Settings(0,0,0,'-') #we'll be writing settings here

        self.tracker_status = False

        #VkApi related
        self.sessions = []
        self.krutka_settings = KrutkaSettings(maxlikes=0,maxreposts=0,posts=[])
        self.regex_for_posts = '(wall)(-?)([0-9]+)(_)([0-9]+)'

        #starting
        self.router.message.register(self.send_welcome, Command('start', 'help'))


        #groups
        self.router.message.register(self.group_view, Command('group_view'), IsAdminFilter(Config))
        self.router.message.register(self.group_add, Command('group_add'), IsAdminFilter(Config))
        self.router.message.register(self.group_add_process, GroupAddingForm.askgroups)
        self.router.message.register(self.group_del, Command('group_delete'), IsAdminFilter(Config))
        self.router.message.register(self.group_del_process, GroupDeletingForm.askgroups)
        
        #tokens
        self.router.message.register(self.token_view, Command('token_view'), IsAdminFilter(Config))
        self.router.message.register(self.token_add, Command('token_add'), IsAdminFilter(Config))
        self.router.message.register(self.token_add_process, TokenAddingForm.asktokens)
        self.router.message.register(self.token_del, Command('token_delete'), IsAdminFilter(Config))
        self.router.message.register(self.token_del_process, TokenDeletingForm.asktokens)
        self.router.message.register(self.login_tokens, Command('login_tokens'), IsAdminFilter(Config))

        #krutka
        self.router.message.register(self.krutka,Command('krutka'), IsAdminFilter(Config))
        self.router.message.register(self.krutka_asklikes,KrutkaForm.askposts)
        self.router.message.register(self.krutka_process,KrutkaForm.asklimits)

        #settings
        self.router.message.register(self.settings_view,Command('settings_view'), IsAdminFilter(Config))
        self.router.message.register(self.settings_set,Command('settings_set'), IsAdminFilter(Config))
        self.router.message.register(self.settings_set_process_limits,SettingsForm.asklimits)
        self.router.message.register(self.settings_set_process_keywords,SettingsForm.askkeywords)

        #tracker
        self.router.message.register(self.start_tracking,Command('start_tracking'), IsAdminFilter(Config))
        self.router.message.register(self.stop_tracking,Command('stop_tracking'), IsAdminFilter(Config))

        #default
        self.router.message.register(self.fallback)


        #keyboard_section
        #menu
        self.commands = [
            types.BotCommand(command='help', description='Вывод помощи'),
            types.BotCommand(command='group_view', description='Посмотреть группы'),
            types.BotCommand(command='group_add', description='Добавить группы'),
            types.BotCommand(command='group_delete', description='Удалить группы'),
            types.BotCommand(command='token_view', description='Посмотреть токены'),
            types.BotCommand(command='token_add', description='Добавить токены'),
            types.BotCommand(command='token_delete', description='Удалить токены'),
            types.BotCommand(command='login_tokens', description='Создать сессии'),
            types.BotCommand(command='krutka', description='Одноразовая крутка'),
            types.BotCommand(command='settings_view', description='Посмотреть настройки'),
            types.BotCommand(command='settings_set', description='Установить настройки'),
            types.BotCommand(command='start_tracking', description='Начать трекинг'),
            types.BotCommand(command='stop_tracking', description='Остановить трекинг')

        ]



####################
#     UTILITY      #
####################


    def run(self):
        logging.basicConfig(level=logging.INFO, stream=sys.stdout)
        asyncio.run(self.main())

    async def main(self) -> None:
        self.loop = asyncio.get_event_loop()
        self.dp.startup.register(self.set_commands)
        await self.dp.start_polling(self.bot)

    def build_group_list(self):
        self.db.cursor.execute(r"SELECT * FROM Communities")
        communities = self.db.cursor.fetchall()
        communities = [Community(*community) for community in communities]
        reply = ''
        for ix,group in enumerate(communities):
            reply += f'{ix}. {group.link}\n'
        return reply, communities

    def build_token_list(self):
        self.db.cursor.execute(r'SELECT * FROM AccessTokens')
        tokens = self.db.cursor.fetchall()
        tokens = [AccessToken(*token) for token in tokens]
        reply = ''
        for ix,token_object in enumerate(tokens):
            if len(token_object.token) > 15:
                reply += f'{ix}. {token_object.token[:15]}... работает: {bool(token_object.valid)}\n'
            else:
                reply += f'{ix}. {token_object.token}... работает: {bool(token_object.valid)}\n'
        return reply, tokens

    async def set_commands(self):
        await self.bot.set_my_commands(self.commands,types.bot_command_scope_default.BotCommandScopeDefault())


    async def fallback(self, message: types.Message):
        #Handle any other unmatched message
        await message.reply("м?)")


    def get_settings(self):
        self.db.cursor.execute(r'SELECT * FROM Settings')
        settings = self.db.cursor.fetchone()
        if settings:
            return Settings(*settings)
        else:
            return Settings(0,0,0,'')

    def update_settings(self,settings):
        self.db.cursor.execute("UPDATE Settings SET maxlikes = ?, maxreposts = ?, keywords = ?", (settings.maxlikes, settings.maxreposts, settings.keywords))
        self.db.conn.commit()


#####################
#     COMMANDS      #
#####################

    async def send_welcome(self, message: types.Message):
        await message.reply(message_start)


# GROUP MANAGEMENT #
####################

    async def group_view(self, message: types.Message):
        reply,_ = self.build_group_list()
        if not reply:
            reply = 'Список отслеживаемых групп пуст!\n/group_add - чтобы добавить'
        await message.reply(reply)

    async def group_add(self, message: types.Message, state: FSMContext):
        await state.set_state(GroupAddingForm.askgroups)
        await message.reply("Отправьте список ссылок на любой пост из группы. Каждая ссылка должна находиться на отдельной строке.")

    async def group_add_process(self, message: types.Message, state: FSMContext):

        rs = re.findall(self.regex_for_posts,message.text)
        temp = []
        for x in rs:
            if len(x) == 5:
                temp.append((''.join(x[1:3]),))
            if len(x) == 4:
                temp.append((x[1],))

        communities = [owner_id for owner_id in temp]
        print(communities)
        try:
            self.db.cursor.executemany("INSERT OR IGNORE INTO Communities VALUES (?);", communities)
            self.db.conn.commit()
            await message.reply('Выполнено, список добавлен')
        except Exception as e:
            await message.reply(f'Возникла ошибка: {e}\nПопробуйте еще раз')
        finally:
            await state.clear()

    async def group_del(self, message: types.Message, state: FSMContext):
        await state.set_state(GroupDeletingForm.askgroups)
        group_list,_ = self.build_group_list()
        await message.reply(f"Отправьте номера удаляемых групп разделенные пробелом или напишите 'все' \n\n{group_list}")

    async def group_del_process(self, message: types.Message, state: FSMContext):
                
        if message.text.lower().strip() == 'все':
            try:
                self.db.cursor.execute('DELETE FROM Communities;')
                self.db.conn.commit()
                await message.reply('Прекращено отслеживание всех групп!')
            except Exception as e:
                await message.reply(f'Возникла ошибка: {e}')
            finally:
                await state.clear()
        else:
            _, communities = self.build_group_list() #communities is a list of community objects with .link parameter
            ids = [int(id) for id in message.text.split(" ") if id.isdigit()]
            reply = 'Удалены id: '
            caused_error = 'id, которые не получилось удалить:\n'
            to_delete = []
            for id in ids:
                try:
                    to_delete.append(communities[id])
                    reply += f'{id} '
                except:
                    caused_error += f'{id} '
            if caused_error != 'id, которые не получилось удалить:\n':
                reply += f'\n{caused_error}'
            try:
                self.db.cursor.executemany("DELETE FROM Communities WHERE link =  ?;", [(group.link,) for group in to_delete])
                self.db.conn.commit()
                await message.reply(reply)
            except Exception as e:
                await message.reply(f'Возникла ошибка: {e}')
            finally:
                await state.clear()


# TOKEN MANAGEMENT #
####################

    async def token_view(self, message: types.Message):
        reply,_ = self.build_token_list()
        if not reply:
            reply = 'Список токенов пуст!\n/token_add - чтобы добавить'
        await message.reply('Список токенов.\nСтатус характеризует последнее состояние токена:\n\n' + reply + '\n/login_tokens - чтобы войти и обновить статусы токенов')

    async def token_add(self, message: types.Message, state: FSMContext):
        await state.set_state(TokenAddingForm.asktokens)
        await message.reply("Отправьте список токенов. Каждый токен должен находиться на отдельной строке.")

    async def token_add_process(self, message: types.Message, state: FSMContext):
        tokens = [(token,False) for token in message.text.split('\n')]
        #print(tokens)

        try:
            self.db.cursor.executemany("INSERT OR IGNORE INTO AccessTokens VALUES (?,?);", tokens)
            self.db.conn.commit()
            await message.reply('Выполнено, список добавлен\n/login_tokens - чтобы попробовать создать сессии')
        except Exception as e:
            await message.reply(f'Возникла ошибка: {e}\nПопробуйте еще раз')
        finally:
            await state.clear()

    async def token_del(self, message: types.Message, state: FSMContext):
        await state.set_state(TokenDeletingForm.asktokens)
        token_list,_ = self.build_token_list()
        await message.reply(f"Отправьте номера удаляемых токенов, разделенные пробелом или напишите 'все' \n\n{token_list}")

    async def token_del_process(self, message: types.Message, state: FSMContext):
                
        if message.text.lower().strip() == 'все':
            try:
                self.db.cursor.execute('DELETE FROM AccessTokens;')
                self.db.conn.commit()
                await message.reply('Таблица токенов очищена!')
            except Exception as e:
                await message.reply(f'Возникла ошибка: {e}')
            finally:
                await state.clear()
        else:
            _, tokens = self.build_token_list() 
            ids = [int(id) for id in message.text.split(" ") if id.isdigit()]
            reply = 'Удалены токены: '
            caused_error = 'Номера токенов, которые не получилось удалить:\n'
            to_delete = []
            for id in ids:
                try:
                    to_delete.append(tokens[id])
                    reply += f'{id} '
                except:
                    caused_error += f'{id} '
            if caused_error != 'Номера токенов, которые не получилось удалить:\n':
                reply += f'\n{caused_error}'
            try:
                self.db.cursor.executemany("DELETE FROM AccessTokens WHERE token =  ?;", [(token_object.token,) for token_object in to_delete])
                self.db.conn.commit()
                await message.reply(reply)
            except Exception as e:
                await message.reply(f'Возникла ошибка: {e}')
            finally:
                await state.clear()


#    SESSIONS     #
###################

    #fills self.sessions with vk_api session instances
    async def login_tokens(self, message: types.Message):
        #1. get token list
        _ ,tokens = self.build_token_list()
        self.sessions = []
        #1. try to create session for each token
        token_statuses = []
        for token_object in tokens:
            try:
                session = vk.VkApi(token=token_object.token)
                session.method('account.getProfileInfo')
                if session:
                    self.sessions.append(session)
                    token_statuses.append((True,token_object.token))
                else:
                    raise Exception("Failed to create session, consturctor returned None")
            except Exception as e:
                token_statuses.append((False,token_object.token))
                print(f'Token: {token_object.token};\n Occured exception {e}')

        self.db.cursor.executemany("UPDATE AccessTokens SET valid = ? WHERE token = ?", token_statuses)
        self.db.conn.commit()

        token_list, _ = self.build_token_list()
        reply = f'Сессии созданы. Текущее состояние списка токенов:\n\n{token_list}'
        print(len(self.sessions))
        await message.reply(reply)            



#      KRUTKA     #
###################


    async def krutka(self, message: types.Message, state: FSMContext):
        await state.set_state(KrutkaForm.askposts)

        if self.sessions:
            await message.reply("Укажите список ссылок на посты, на которые крутим.\nНеобходимо указать по одной ссылке на строку.")
        else:
            await message.reply("Не найдено активных сессий.\n/token_view - посмотреть список токенов\n/login_tokens - создать сессии по имеющимся токенам")
            await state.clear()

    async def krutka_asklikes(self, message: types.Message, state: FSMContext):
        await state.set_state(KrutkaForm.asklimits)

        rs = re.findall(self.regex_for_posts,message.text)
        temp = []
        for x in rs:
            if len(x) == 5:
                temp.append((''.join(x[1:3]),x[4]))
            if len(x) == 4:
                temp.append((x[1],x[3]))



        if not temp:
            await state.clear()
            await message.reply("Не был указан ни один пост. Обрываю операцию.")
        else:
            self.krutka_settings.posts = temp
            await message.reply(f"Получено {len(self.krutka_settings.posts)} постов.\nВведите лимиты лайков и репостов, разделенные пробелом.\nНапример, '50 0'\nЛимит = 0 означает, что данный параметр крутиться не будет.")


    async def krutka_process(self, message: types.Message, state: FSMContext):
        params = message.text.split(" ")
        if len(params) != 2:
            await state.clear()
            await message.reply("Указано не 2 параметра, обрываю операцию. Параметры должны быть 2 числами, разделенными пробелом") 
            return 

        params = [x.strip() for x in params if x.isdigit()] #clears out non-numeric strings

        if len(params) != 2:
            await state.clear()
            await message.reply("Было указано 2 параметра, но не числовые. Обрываю операцию.")
            return  

        self.krutka_settings.maxlikes = int(params[0])             
        self.krutka_settings.maxreposts = int(params[1])

        process_message_text = f"Параметры накрута:\n\nПосты:\n{"\n".join([str(x) for x in self.krutka_settings.posts])}\n\nЛайки: {self.krutka_settings.maxlikes}\nРепосты: {self.krutka_settings.maxreposts}"
        process_message = await message.reply(process_message_text)
                       


        with futuress.ThreadPoolExecutor(max_workers=len(self.sessions)) as executor:
            
            #initializing counters
            counters = {}
            for post in self.krutka_settings.posts:
                counters[post] = [0,0]


            lock = th.Lock()
            fthreads = [executor.submit(self.krutka_task, sess, self.krutka_settings, counters, lock) for sess in self.sessions]
            print(len(self.sessions))
            failed_futures = 0
            completed_futures = 0
            for future in futuress.as_completed(fthreads):
                try:
                    #status - 0 if failed, 1 if exited properly
                    status, description = future.result()
                    if status:
                        completed_futures += 1
                    else:
                        failed_futures += 1
                    print(description)
                except Exception as exc:
                    print(exc)
                    failed_futures += 1
                finally:
                    process_message_new = f'{process_message_text}\n\nВышедшие потоки: {completed_futures}\nУмершие потоки: {failed_futures}'
                    process_message = await process_message.edit_text(process_message_new)

        counters_string = ''
        for post, stats in counters.items():
            counters_string += f'vk.com/wall{post[0]}_{post[1]} - {stats[0]}/{stats[1]}\n' 
        await process_message.edit_text(f'Результаты накрута:\nЛимиты: {self.krutka_settings.maxlikes}/{self.krutka_settings.maxreposts}\n\nПост/Лайк/Репост:\n{counters_string}\n\nВышедшие потоки: {completed_futures}\nУмершие потоки: {failed_futures}',disable_web_page_preview=True) 


    @staticmethod
    def krutka_task(session, settings, counters, lock):
        try:
            acc = session.method('account.getProfileInfo')
        except Exception as exc:
            return 0,f'{session} could not start: {exc}'

        for post in settings.posts:
            owner_id,item_id = post
            like, repost = False,False #init like/repost switches
            reposted = 0 #init if_reposted counter (b.c. isLiked API method returns if reposted on the wall, not in messages)
            params = dict(type='post', owner_id=int(owner_id), item_id=int(item_id)) #common params for API requests

            try:
                before = list(session.method('likes.isLiked',values=params).values())
            except Exception as exc:
                print(f'Exception occured in {session}: {exc} - skipping!')
                continue


            with lock:
                #print(f'[THREAD {session}] post: {post},counters: {counters[post]}')
                if counters[post][0] < settings.maxlikes:
                    like = True
                    counters[post][0] += 1
                else:
                    print(f'[THREAD {session}] post: {post},counters: {counters[post]} - skipping job')

                if counters[post][1] < settings.maxreposts:
                    repost = True
                    counters[post][1] += 1
                else:
                    print(f'[THREAD {session}] post: {post},counters: {counters[post]} - skipping job')
        

            try:
                if like:
                    session.method('likes.add',values=params)
                if repost:
                    session.method('messages.send',values=dict(user_id=acc['id'], random_id=0,attachment=f'wall{owner_id}_{item_id}'))
                    reposted = 1
            except Exception as exc:
                print(f"Exception in thread {session}: {exc}")

            after = list(session.method('likes.isLiked',values=params).values())
            resulting_stats = ((owner_id,item_id),after[0] - before[0], reposted)


            with lock:
                #updating like counter for this post
                if like:
                    counters[post][0] -= 1-resulting_stats[1]
                #updating respot counter for this post
                if repost:
                    counters[post][1] -= 1-resulting_stats[2] 

        return 1, f'id{acc['id']} finished'


#     TRACKER     #
###################

    async def settings_view(self, message: types.Message):
        await message.reply(f"Текущее состояние настроек.\n\nЛимит лайков: {self.settings.maxlikes}\nЛимит репостов: {self.settings.maxreposts}\nКлючевые слова:\n{self.settings.keywords}\n\n/settings_set - установить настройки")
    
    async def settings_set(self, message: types.Message, state: FSMContext):
        await state.set_state(SettingsForm.asklimits)
        await message.reply("Смена настроек: шаг 1\nУкажите лимиты лайков/репостов через пробел.\nНапример: '50 0' - нулевой лимит означает, что данный параметр крутиться не будет")


    async def settings_set_process_limits(self, message: types.Message, state: FSMContext):
        await state.set_state(SettingsForm.askkeywords)

        params = message.text.split(" ")
        if len(params) != 2:
            await state.clear()
            await message.reply("Указано не 2 параметра, обрываю операцию. Параметры должны быть 2 числами, разделенными пробелом") 
            return 

        params = [x.strip() for x in params if x.isdigit()] #clears out non-numeric strings

        if len(params) != 2:
            await state.clear()
            await message.reply("Было указано 2 параметра, но не числовые. Обрываю операцию.")
            return  

        self.dummy_settings.maxlikes = params[0]
        self.dummy_settings.maxreposts = params[1]
        await message.reply("Смена настроек: шаг 2\nУкажите ключевые слова, на каждой строке по фразе или слову.\nНапример:\nпримерная фраза 2\nпримерная фраза 1\n\nОтправьте \"-\", чтобы лайкались все выходящие посты в указанных группах")

    async def settings_set_process_keywords(self, message: types.Message, state: FSMContext):
        self.dummy_settings.keywords = message.text
        await state.clear()
        #Actual settings are stored in database
        try:
            self.update_settings(self.dummy_settings)
            self.settings = self.get_settings()
            await message.reply(f'Смена настроек: успех\n\nЛимит лайков: {self.settings.maxlikes}\nЛимит репостов: {self.settings.maxreposts}\nКлючевые слова:\n{self.settings.keywords}')
        except Exception as exc:
            self.settings = self.get_settings()
            await message.reply(f'Смена настроек:\nОшибка - не получилось записать настройки в базу данных.\nОставляю старые настройки.\n\nЗначение ошибки:\n{exc}')
            return 


    async def start_tracking(self, message: types.Message):
        self.tracker_status = True
        self.loop.create_task(self.tracking_loop(message))

    async def stop_tracking(self, message: types.Message):
        self.tracker_status = False
        await message.reply('Накрут остановлен')


    async def tracking_loop(self, message: types.Message):
        process_message = await message.reply("Статистика крутки.\n\n/settings_view - чтобы посмотреть параметры")
        cnt = 1
        while self.tracker_status == True:
    
            pack_length = len(self.sessions)
            if self.settings.keywords != '-':
                keywords = self.settings.keywords.split('\n')
            else:
                keywords = []
    
            if not pack_length:
                return await message.reply("Не найдено активных сессий.\n/token_view - посмотреть список токенов\n/login_tokens - создать сессии по имеющимся токенам")

                
    
            tasks = []
            _, group_list = self.build_group_list() #group_list contains Community objects
            for i in range(0,len(group_list),pack_length):
                tasks.append(group_list[i:i+pack_length]) #i.e. each 
                
            tasks = list(map(list, zip_longest(*tasks))) #i-th task is a set of links for i-th session
            posts_tracked = []
    
    
            with futuress.ThreadPoolExecutor(max_workers=pack_length) as executor:
    
                completed_futures, failed_futures = 0,0
                fthreads = [executor.submit(self.tracking_check_new_posts, self.sessions[i], tasks[i], keywords) for i in range(len(tasks))]
                for future in futuress.as_completed(fthreads):
                    try:
                        posts = future.result()
                        if posts:
                            posts_tracked += posts
                        completed_futures += 1
                        print(posts)
                    except Exception as exc:
                        print(exc)
                        failed_futures += 1
                    finally:
                        pass
    
                #initializing counters
                counters = {}
                for post in posts_tracked:
                    counters[post] = [0,0]
    
    
                lock = th.Lock()
                krutka_settings = KrutkaSettings(maxlikes=self.settings.maxlikes, maxreposts=self.settings.maxreposts,posts=posts_tracked)
                fthreads = [executor.submit(self.krutka_task, sess, krutka_settings, counters, lock) for sess in self.sessions]
                completed_futures, failed_futures = 0,0
                for future in futuress.as_completed(fthreads):
                    try:
                        #status - 0 if failed, 1 if exited properly
                        status, description = future.result()
                        if status:
                            completed_futures += 1
                        else:
                            failed_futures += 1
                        print(description)
                    except Exception as exc:
                        print(exc)
                        failed_futures += 1
    
            counters_string = ''
            for post, stats in counters.items():
                counters_string += f'vk.com/wall{post[0]}_{post[1]} - {stats[0]}/{stats[1]}\n' 
            await process_message.edit_text(f'Результаты накрута ({cnt}):\nЛимиты: {self.settings.maxlikes}/{self.settings.maxreposts}\n\nПост/Лайк/Репост:\n{counters_string}\n\nВышедшие потоки: {completed_futures}\nУмершие потоки: {failed_futures}',disable_web_page_preview=True)
            cnt+=1
            await asyncio.sleep(30) 
            
            

    @staticmethod
    def tracking_check_new_posts(session, communities, keywords):
        #We consider a Post as a tuple of owner_id and item_id
        #In this func the session runs through all communities given to it and look for posts with keywords in it
        #returns a list of Posts

        posts = []
        for community in communities:
            if community:
                try:
                    rs = session.method('wall.get', values=dict(owner_id=int(community.link), count=1))
                    post = rs['items'][0]
                    text = post['text']

                    if any(keyword in text for keyword in keywords):
                        posts.append((community.link,post['id']))
                    
                    print(f'{session} says: {post['id']} has text {post['text']} at {community.link}')
                except Exception as exc:
                    print(f'{session} says: {exc} for {community}')

            else:
                continue

        return posts
vkbot = BotWrapper(Config)
vkbot.run()
