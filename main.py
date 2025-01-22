import vk_api as vk
import threading as th

#tokens = ['vk1.a.H7HypAnZvxPc9AlKSaFkefCeKL09C3ceZip6dmo42XvIKcYj7XvCxXRa-Q1roI94SrEm9UR3bG0UmxQPjNPqovd0t0W5jHyWu304nIAsMKgMzxEE8dz8ZswkMltep84-1xtAGAYzl7IOL3NtJnTxxQnepPdHMFz2A0l1mEIAGRQumgbXC1qfkk-G0MAEA3HKAqTM70gtLJMUCy-_meHTKA',
#'vk1.a.epofzzANPaae8o4RhrL0bDMFUA-y9Q75XZbdlnmPqMT1Xdm6frkF3Ogp-ifGoWryk08OQAa0-dSaJdBwMFiuf1M5SkrjSBQYsYI37Q7PtkIriyxiv2RDwqCQQxrcjfELty-wkwScli5JgcHvIFOZpTYZsUy80He2BaqwgwjKM2RJDvZjh4izlQ0xgx49ebtVUAaDgUdmeSlg4E6QDs_fcQ',
#]
#
#vk1.a.epofzzANPaae8o4RhrL0bDMFUA-y9Q75XZbdlnmPqMT1Xdm6frkF3Ogp-ifGoWryk08OQAa0-dSaJdBwMFiuf1M5SkrjSBQYsYI37Q7PtkIriyxiv2RDwqCQQxrcjfELty-wkwScli5JgcHvIFOZpTYZsUy80He2BaqwgwjKM2RJDvZjh4izlQ0xgx49ebtVUAaDgUdmeSlg4E6QDs_fcQ

with open('tokens.txt','r') as file:
	tokens = file.readlines()


posts = ['161486117_2408767',
		'161486117_2411343',
		'161486117_2411342',
		'161486117_2411339',
		'161486117_2411333',
		'161486117_2411330']

#vk.VkApi.captcha_handler

#sessions = [vk.VkApi(token=token,captcha_handler=None) for token in tokens]

#session = vk.VkApi(token=tokens[0])

token = 'vk1.a.Jb9jygg1R0gH_UVwRbPvOaLJJHo_VDfJ9y7-a4VCaM466_GoHK9wivU6j2yAV7t2ENgo7nONQm_ryrGRKYiS6Fc9c-1-G-9asppjal2CAyrDus0kgmNaYA4sBt4QWq-CDsIzQbBUeG7KVSSBRHSS6CcI2f83b5F6yELeo1vXzOuC5IrDbVQdpjXFlg87DKOv9lHbGmNEsosowEUB_tJShw'
session = vk.VkApi(token=token,captcha_handler=None)
acc = session.method('account.getProfileInfo')
full_attachment = 'wall-45172096_2286918'
session.method('messages.send', values=dict(user_id=acc['id'], random_id=0,attachment=full_attachment))



#1. tracking postov
#2. like, reposti, podpiski, zakladki (faves)


#1. crud для списка постов и списка токенов
#2. трекинг постов и циклическое выполнение действий для них



##1. Tokeni
#/token_add - кормишь лист токенов либо 1 токен и оно добавляет в текстовый файл и сразу перепаршивает базу
#/token_view - посмотреть лист токенов
#/token_delete - выводит список токенов по номерам, выбираешь циферкой какой удалить
##2. Tracker
#/group_add - добавляет группы в список по id 
#/group_view - посмотреть список групп 
#/group_delete - удалить список групп по номерам 
#/start - начать трекинг
#/stop - остановить трекинг
#/set_max_likes - установить лимит лайков
#/set_max_reposts - установить лимит репостов
#/set_keywords - установить ключевые слова
#/view_settings - выведем настройки (лайки,репосты,ключевые слова)
##3. Отдельная крутка
#/krutka - запустить N потоков-аккаунтов по указанным постам с отдельными лимитами лайков-репостов

