import os
from telethon import Button
from config import API_ID, API_HASH
from db import set_authed
from gifts import GIFTS
from utils import (
    get_session_path, get_entity_from_input, 
    get_stars_balance, send_gift, validate_session, get_user_client
)
from auth import states, start_auth

async def start_send_flow(bot, event):
    uid = event.sender_id
    
    if not await validate_session(uid):
        await event.respond(
            "Ooops! You are not authenticated yet! Please authenticate yourself before using this command :]",
            buttons=[Button.inline("Authenticate", data="auth")]
        )
        return

    if uid in states and states[uid].get("state") in ("AWAITING_TARGET", "AWAITING_AMOUNT", "AWAITING_COMMENT", "AWAITING_GIFT"):
        return

    data = {"target": None, "amount": None, "comment": None, "gift": None}
    states[uid] = {"state": "AWAITING_TARGET", "data": data, "flow_msg_id": None}
    msg = await event.respond("Who do you want to send gift to? (UID or Username):")
    states[uid]["flow_msg_id"] = msg.id

async def update_flow_message(bot, event, uid, field_name, prompt):
    state = states[uid]
    data = state["data"]
    
    text = ""
    if data.get("target"):
        text += f"**User:** {data['target']}\n"
    if data.get("amount"):
        text += f"**Amount:** {data['amount']}\n"
    if data.get("comment") is not None:
        text += f"**Comment:** {data['comment'] if data['comment'] else '(none)'}\n"
    if data.get("gift"):
        text += f"**Gift:** {data['gift']}\n"
    text += f"\n{prompt}"
    
    if state["flow_msg_id"]:
        await bot.edit_message(event.chat_id, state["flow_msg_id"], text, parse_mode='markdown')
    else:
        msg = await event.respond(text, parse_mode='markdown')
        state["flow_msg_id"] = msg.id

async def show_gift_selection(bot, event, uid):
    state = states[uid]
    text = "**User:** {}\n**Amount:** {}\n**Comment:** {}\n\n**Which gift do you want to send?**".format(
        state["data"]["target"],
        state["data"]["amount"],
        state["data"]["comment"] if state["data"]["comment"] else "(none)"
    )
    
    buttons = []
    gift_names = list(GIFTS.keys())
    for i in range(0, len(gift_names), 2):
        row = []
        for j in range(2):
            if i+j < len(gift_names):
                name = gift_names[i+j]
                row.append(Button.inline(name, data=f"gift_{name}"))
        buttons.append(row)
    buttons.append([Button.inline("Cancel", data="cancel")])

    if state["flow_msg_id"]:
        await bot.edit_message(event.chat_id, state["flow_msg_id"], text, buttons=buttons, parse_mode='markdown')
    else:
        msg = await event.respond(text, buttons=buttons, parse_mode='markdown')
        state["flow_msg_id"] = msg.id

async def show_summary(bot, event, uid):
    state = states[uid]
    data = state["data"]
    text = "**User:** {}\n**Amount:** {}\n**Comment:** {}\n**Gift:** {}\n\n**Confirm or cancel:**".format(
        data["target"], data["amount"], data["comment"] if data["comment"] else "(none)", data["gift"]
    )
    buttons = [[Button.inline("Cancel", data="cancel"), Button.inline("Send", data="send")]]
    await bot.edit_message(event.chat_id, state["flow_msg_id"], text, buttons=buttons, parse_mode='markdown')

async def cancel_flow(bot, event, uid):
    if uid in states:
        if states[uid].get("flow_msg_id"):
            await bot.delete_messages(event.chat_id, [states[uid]["flow_msg_id"]])
        del states[uid]
    await event.answer("Cancelled.")
    await event.respond("Operation cancelled.")

async def send_gifts(bot, event, uid):
    state = states.get(uid)
    if not state or state["state"] != "SUMMARY":
        await event.answer("No active session.")
        return
    
    data = state["data"]
    target = data["target"]
    amount = data["amount"]
    comment = data["comment"]
    gift_name = data["gift"]
    gift_id = GIFTS[gift_name]

    client = await get_user_client(uid)
    if not client:
        await event.answer("Session invalid. Please re-authenticate.")
        set_authed(uid, 0)
        await start_auth(bot, event, uid)
        return

    try:
        peer = await get_entity_from_input(client, target)
    except Exception:
        await event.answer("Invalid target user. Please try again.")
        await client.disconnect()
        return

    balance = await get_stars_balance(client)
    if balance < amount:
        await event.answer("You don't have enough stars to complete this action! Please buy stars and retry.")
        await client.disconnect()
        return

    sent = 0
    for i in range(amount):
        try:
            await send_gift(client, peer, gift_id, comment)
            sent += 1
        except Exception as e:
            err = str(e).lower()
            if "balance" in err or "stars" in err:
                await event.respond("Insufficient stars. Stopping.")
                break
            if "gift_send_forbidden" in err:
                await event.respond("This user has disabled receiving gifts. Stopping.")
                break
            if "auth" in err or "session" in err:
                await event.respond("Authentication error. Please re-authenticate.")
                set_authed(uid, 0)
                await client.disconnect()
                session_path = get_session_path(uid)
                if os.path.exists(session_path):
                    os.remove(session_path)
                await start_auth(bot, event, uid)
                return
            await event.respond(f"Failed on #{i+1}: {str(e)}")
    
    await client.disconnect()

    try:
        target_user = await bot.get_entity(target)
        target_mention = f"@{target_user.username}" if target_user.username else target
    except:
        target_mention = target

    final_text = f"You sent {gift_name} to {target_mention}!"
    if sent < amount:
        final_text += f" (Only {sent} sent)"

    buttons = [[Button.inline("🔄 Send Gift", data="send_gift")]]
    await bot.edit_message(event.chat_id, state["flow_msg_id"], final_text, buttons=buttons)
    await event.answer("Done.")
    del states[uid]

async def handle_flow_message(bot, event, uid, state):
    if state["state"] == "AWAITING_TARGET":
        target_input = event.message.text.strip()
        await event.delete()
        if not target_input:
            return
        state["data"]["target"] = target_input
        state["state"] = "AWAITING_AMOUNT"
        await update_flow_message(bot, event, uid, "Amount", "How many do you want to send?")
        
    elif state["state"] == "AWAITING_AMOUNT":
        amount_str = event.message.text.strip()
        await event.delete()
        if not amount_str.isdigit():
            await event.respond("Please enter a valid number.")
            return
        amount = int(amount_str)
        if amount < 1 or amount > 1000:
            await event.respond("Please enter a valid number between 1 and 1000.")
            return
        state["data"]["amount"] = amount
        state["state"] = "AWAITING_COMMENT"
        await update_flow_message(bot, event, uid, "Comment", "Do you want to add a comment to the gifts? (Type No or no, if you don't want to):")
        
    elif state["state"] == "AWAITING_COMMENT":
        comment = event.message.text.strip()
        await event.delete()
        if comment.lower() == "no":
            comment = ""
        state["data"]["comment"] = comment
        state["state"] = "AWAITING_GIFT"
        await show_gift_selection(bot, event, uid)
