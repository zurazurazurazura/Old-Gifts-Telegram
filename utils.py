import os
from config import SESSIONS_DIR, API_ID, API_HASH
from telethon import TelegramClient
from telethon.tl.types import InputInvoiceStarGift, TextWithEntities, DataJSON
from telethon.tl.functions.payments import GetPaymentFormRequest, SendStarsFormRequest

def get_session_path(uid):
    return os.path.join(SESSIONS_DIR, f"{uid}.session")

async def delete_messages(bot, chat, msg_ids):
    if msg_ids:
        await bot.delete_messages(chat, msg_ids)

async def get_entity_from_input(client, input_str):
    if input_str.isdigit():
        return await client.get_input_entity(int(input_str))
    if input_str.startswith("@"):
        return await client.get_input_entity(input_str)
    return await client.get_input_entity(input_str)

async def get_stars_balance(client):
    try:
        from telethon import functions, types
        result = await client(functions.payments.GetStarsStatusRequest(peer=types.InputPeerSelf()))
        total = result.balance.amount + result.balance.nanos / 1_000_000_000
        return total
    except:
        return 0.0

async def send_gift(client, peer, gift_id, message):
    invoice = InputInvoiceStarGift(
        peer=peer,
        gift_id=gift_id,
        message=TextWithEntities(text=message, entities=[]),
        hide_name=False
    )
    form = await client(GetPaymentFormRequest(
        invoice=invoice,
        theme_params=DataJSON(data="{}")
    ))
    await client(SendStarsFormRequest(
        form_id=form.form_id,
        invoice=invoice
    ))

async def validate_session(uid):
    from db import set_authed
    session_path = get_session_path(uid)
    
    if not os.path.exists(session_path):
        set_authed(uid, 0)
        return False
    
    try:
        test_client = TelegramClient(session_path, API_ID, API_HASH)
        await test_client.connect()
        if not await test_client.is_user_authorized():
            set_authed(uid, 0)
            await test_client.disconnect()
            return False
        await test_client.disconnect()
        return True
    except:
        set_authed(uid, 0)
        return False

async def get_user_client(uid):
    session_path = get_session_path(uid)
    if not os.path.exists(session_path):
        return None
    
    client = TelegramClient(session_path, API_ID, API_HASH)
    try:
        await client.connect()
        if not await client.is_user_authorized():
            await client.disconnect()
            return None
        return client
    except:
        return None
