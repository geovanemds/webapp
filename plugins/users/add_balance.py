import math
from typing import Union

from pyrogram import Client, filters
from pyrogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from config import ADMIN_CHAT
from database import cur, save
from utils import create_mention, get_lara_info, get_support_user, insert_sold_balance


@Client.on_callback_query(filters.regex(r"^add_saldo$"))
async def add_saldo(c: Client, m: CallbackQuery):
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    "💠 Pix automático", callback_data="add_saldo_auto"
                ),
                InlineKeyboardButton("🤖 Pix manual", callback_data="add_saldo_manual"),
            ],
            [
                InlineKeyboardButton("🔙 Voltar", callback_data="start"),
            ],
        ]
    )

    await m.edit_message_text(
        """[ ](https://i.ibb.co/pv71sFN/pix-1.jpg)<b>💵 Adicionar saldo</b>
<i>- Aqui abaixo você poderá adicionar saldo de duas formas, ou <b>pix automático</b> ou <b>pix manual</b>.</i>""",
        reply_markup=kb,
    )


@Client.on_callback_query(filters.regex(r"^add_saldo_manual$"))
async def add_saldo_manual(c: Client, m: CallbackQuery):
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton("🔙 Voltar", callback_data="add_saldo"),
            ],
        ]
    )

    pix_name, pix_key = get_lara_info()

    support_user = get_support_user()
    valor_min = 1
    details = (
        f"\n\n<i>⚠️ Não envie um valor menor que R$ {valor_min},00 pois se você enviar perderá seu dinheiro.</i>"
        if valor_min
        else ""
    )
    await m.edit_message_text(
        f"""<b>🤖 Pix manual</b>
Para adicionar saldo manualmente, copie a chave PIX abaixo e faça o pagamento, após feito mande o comprovante para o dono do BOT, assim seu saldo será adicionado por ele.

<b>🏦 DADOS DA CONTA 🏦</b>

<b>Nome:</b> <code>{pix_name}</code>
<b>Chave Pix:</b> <code>{pix_key}</code>

<b>Envie o comprovante para {get_support_user()}</b>
{details}""",
        reply_markup=kb,
    )


@Client.on_message(filters.regex(r"/resgatar (?P<gift>\w+)$"))
@Client.on_callback_query(filters.regex(r"^resgatar (?P<gift>\w+)$"))
async def resgatar_gift(c: Client, m: Union[CallbackQuery, Message]):
    user_id = m.from_user.id
    gift = m.matches[0]["gift"]

    if isinstance(m, Message):
        send = m.reply_text
    else:
        send = m.edit_message_text

    try:
        value = cur.execute(
            "SELECT value from gifts WHERE token = ?", [gift]
        ).fetchone()[0]
    except:
        return await send("<b>⚠️ Gift card não existente ou já resgatado.</b>")

    cur.execute("DELETE FROM gifts WHERE token = ?", [gift])

    cur.execute(
        "UPDATE users SET balance = balance + ? WHERE id = ?", [value, user_id]
    ).fetchone()

    new_balance = cur.execute(
        "SELECT balance FROM users WHERE id = ?", [user_id]
    ).fetchone()[0]

    mention = create_mention(m.from_user)
    insert_sold_balance(value, user_id, "manual")
    base = f"""[ ](https://i.ibb.co/yYw5YPH/ac-asesores-saldos-corrientes-ahorros.jpg)💸 {mention} 
    
- resgatou um gift card de <b>R${value}</b>
- Novo saldo: <b>R${new_balance}</b>
- Gift card: <code>{gift}</code>


"""

    await c.send_message(ADMIN_CHAT, base)

    if isinstance(m, CallbackQuery):
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        "🛒 Voltar ao bot",
                        url=f"https://t.me/{c.me.username}?start=start",
                    ),
                ],
            ]
        )
        await send(
            f"<b>🎉 {m.from_user.first_name} resgatou R$ {value} no bot via gift card.</b>",
            reply_markup=kb,
        )
    else:
        await send(
            f"[  ](https://i.ibb.co/yYw5YPH/ac-asesores-saldos-corrientes-ahorros.jpg)<b>🎉 Agora sim 👏 foi adicionado R$ {value} em sua conta no bot.</b>"
        )

    
    refer = cur.execute("SELECT refer FROM users WHERE id = ?", [user_id]).fetchone()[0]

    if refer:
        quantity = math.floor((value / 100) * 5)  # 5% normalizado para int.
        if quantity > 0:
            mention = create_mention(m.from_user, with_id=False)

            cur.execute(
                "UPDATE users SET balance = balance + ? WHERE id = ?",
                [quantity, refer],
            ).fetchone()

            await c.send_message(
                int(refer),
                f" Seu referenciado {mention} adicionou saldo no bot e você recebeu {quantity} de saldo.",
            )
    
    save()
