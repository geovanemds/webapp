import html
from asyncio import Lock
from datetime import datetime, timedelta
from functools import wraps
from typing import Callable, Iterable, Optional, Tuple, Union
import json
from random import randint
import httpx
from async_lru import alru_cache
from pyrogram import Client
from pyrogram.types import CallbackQuery, User

from database import cur

timeout = httpx.Timeout(40, pool=None)

hc = httpx.AsyncClient(http2=True, timeout=timeout)


lock = Lock()


def is_bot_online() -> bool:
    """Retorna `True` se o bot está online ou `False` se ele está em manutenção."""

    q = cur.execute("SELECT is_on from bot_config")

    return bool(q.fetchone()[0])


def is_user_banned(user_id: int) -> bool:
    """Retorna `True` se o usuário está banido ou `False` caso contrário."""

    q = cur.execute("SELECT is_blacklisted from users WHERE id = ?", [user_id])
    res = q.fetchone()

    return bool(res[0] if res else res)


def get_lara_info() -> Tuple[str, str]:
    """Retorna uma tupla contendo o nome da lara e chave Pix."""

    q = cur.execute("SELECT lara_name, lara_key from bot_config")

    return q.fetchone()


def get_support_user() -> str:
    """Retorna uma string contendo o username do usuário de suporte."""

    q = cur.execute("SELECT support_user from bot_config")

    return q.fetchone()[0]


def get_news_user() -> str:
    """Retorna uma string contendo o username do canal de notícias."""

    q = cur.execute("SELECT channel_user from bot_config")

    return q.fetchone()[0]


def get_info_wallet(user_id: int) -> str:
    base = """<b>🏦 Carteira:</b>
<b> ├ ID:</b> <code>{}</code>
<b> ├💰 Saldo: R$ {}</b>
<b> └💎 Pontos: {}</b>"""
    rt = cur.execute(
        "SELECT id, balance, balance_diamonds FROM users WHERE id=?", [user_id]
    ).fetchone()
    return base.format(*rt)


def insert_buy_sold(lista: Iterable = "sequence"):
    list_itens = "number, month, year, cvv, level, added_date, vendor, bank, country, cpf, name, owner, plan, is_checked"
    cur.execute(
        f"INSERT INTO cards_sold({list_itens}) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        lista,
    )


def insert_sold_balance(value: int, owner: int, type_add_saldo: str, quantity: int = 1):
    cur.execute(
        """INSERT INTO sold_balance(type, value, owner, quantity) VALUES(?, ?, ?, ?)""",
        [type_add_saldo, value, owner, quantity],
    )


async def msg_buy_off_user(
    user_id: int,
    card: str,
    vendor: str,
    country: str,
    bank: str,
    level_cc: str,
    price: int,
    received_points: float,
    dados: Optional[Tuple[str, str]] = None,
) -> str:
    cpf, name = dados if dados else await get_person()
    bdados = f"""\n<b>Nome</b> <code>{name}</code>\n<b>Cpf:</b> <code>{cpf}</code>\n"""

    new_balance = cur.execute(
        "SELECT balance FROM users WHERE id = ?", [user_id]
    ).fetchone()[0]

    produto = f"""<b>💳 Produto:</b>
<b>Card:</b> <code>{card}</code>
<b>Bandeira:</b> <code>{vendor}</code>
<b>País: </b><code>{country}</code>
<b>Banco: </b> <code>{bank}</code>"""

    base = f"""<b>☑️ Compra efetuada!</b>
<b>- {level_cc}</b>
<b>- Preço: R$ {price}</b>
<b>- Novo Saldo: R$ {new_balance}</b>
<b>- Pontos recebidos: {received_points}</b>


<b>NÃO GARANTIMOS A APROVAÇÃO</b>
<b>NÃO GARANTIMOS SALDO</b>

{produto}
{bdados}
Produto comprado com gate off, ou seja, sem troca."""
    return base


async def msg_buy_user(
    user_id: int,
    card: str,
    vendor: str,
    country: str,
    bank: str,
    level_cc: str,
    price: int,
    received_points: float,
    dados: Optional[Tuple[str, str]] = None,
) -> str:
    cpf, name = dados if dados else await get_person()

    time = cur.execute("SELECT time_exchange FROM bot_config").fetchone()[0]

    exchange_on = bool(cur.execute("SELECT exchange_is FROM bot_config").fetchone()[0])
    time_exchange = int(
        cur.execute("SELECT time_exchange FROM bot_config").fetchone()[0]
    )
    time_max = (datetime.now() + timedelta(minutes=time_exchange)).strftime(
        "%d/%m/%Y %H:%M:%S"
    )
    info = (
        f"<b>⏰ TEMPO MAXIMO PARA O REEMBOLSO {time} Minutos</b>"
        if exchange_on
        else ""
    )
    new_balance = cur.execute(
        "SELECT balance FROM users WHERE id = ?", [user_id]
    ).fetchone()[0]

    number, month, year, cvv = card.split("|")

    base = f"""<b>✅ Compra Efetuada! ✅

⚠️ GARANTIMOS SOMENTE LIVE!</b>

<b>💳Cartão:</b> <code>{number}</code>
<b>📆Data:</b> <code>{month}/{year}</code>
<b>🔐Cvv:</b> <code>{cvv}</code>
<b>🛍Cartão Formatado:</b> <code>{card}</code>

</b>**👤Dados Abaixo**</b>
<b>📄Nome:</b> <code>{name}</code>
<b>🗄CPF:</b> <code>{cpf}</code>

<b>🎚️Nível:</b> {level_cc}
<b>💳Bandeira:</b> {vendor}
<b>🏳️País:</b> {country}
<b>🏦Banco:</b> {bank}

</b>**🔥GRUPO DE METODOS VIP [AQUI](t.me/+dPN2C931ULg5ZTZh)**</b>
</b>**💸CC APROVOU CHAME O [DONO](t.me/hydra171)**</b>

<b>💰Preço do cartão:</b> R$ {price}
<b>🧨Seu Saldo Restante:</b> R$ {new_balance}
<b>🤑Pontos recebidos: {received_points}</b>

<b>{info}</b>"""
    return base


async def msg_mix_buy_user(
    user_id,
    level_cc,
    price,
    received_points,
) -> str:
    time = cur.execute("SELECT time_exchange FROM bot_config").fetchone()[0]

    swap_is = cur.execute("SELECT exchange_is FROM bot_config").fetchone()[0]

    new_balance = cur.execute(
        "SELECT balance FROM users WHERE id = ?", [user_id]
    ).fetchone()[0]

    troca = (
        f"\nVocê tem {time * level_cc} minutos para trocar se alguma CC não estiver live."
        if swap_is == 1
        else ""
    )
    base = f"""<b>✅ Compra efetuada!</b>
<b>📦 **Mix:** {level_cc}</b>
<b>⚜️ **Preço:** R$ {price}</b>
<b>🤑 **Novo Saldo:** R$ {new_balance}</b>"""
    return base
def msg_group_adm(
    mention, card, level, type_buy, price, gate, new_balance, vendor
) -> str:
    produto = f"""[ ](https://i.ibb.co/92SbSN9/Digio-uber-projeto-vf-cartao-OP3-540x393-ALPHA-gif.gif)</b>✅ Nova Venda Efetuada!!</b>

<b>👤 **{mention}** **Comprou Uma cc**<b>
<b>⚜️ **Preço:**</b> R$ {price}
<b>🏳️ **Bandeira:**</b> {vendor}
<b>🛰 **Nível:**</b> {level}

🏆 **Faça Sua Compra Agora**
🤖 [Nossa Store](t.me/hydra7storebot)"""
    return produto
def msg_mix_group_adm(mention, quantity, price, new_balance) -> str:
    produto = f"""
<b>📦 </b> {mention} <b>comprou Mix {quantity}</b>
<b>⚜️Preço: R$ {price}</b>
<b>💰Novo saldo: R$ {new_balance}</b>"""
    return produto


async def get_price(price_type: str, price_name: str) -> int:
    """
    Retorna uma int contendo o preço do item.

    O parâmetro `price_type` será o tipo de valor para pesquisar, ex.:
        UNIT (Por level) ou BIN (Por bin).
    O parâmetro `price_name` será o valor para pesquisa, ex.:
        GOLD (Por level) ou 550209 (Por bin).

    Por padrão, caso a compra for de tipo `BIN`, a função tentará obter
    o preço especifico da bin, e caso falhe, procurará o nível em `UNIT`,
    e caso falhe novamente, procurará o valor de INDEFINIDO em UNIT,
    e caso falhe novamente fará um "fallback" para R$ 12.
    """

    if price_type == "bin":
        price = cur.execute(
            "SELECT price FROM prices WHERE price_type = ? AND price_name LIKE ?",
            [price_type, price_name],
        ).fetchone()

        if price:
            return price[0]

        # Caso não exista preço de bin, pesquisa o level:
        new_price_type = "unit"
        price_name = (await search_bin(price_name))["level"]
    else:
        new_price_type = price_type

    # Caso seja unit ou a bin acima não tinha preço:
    price = cur.execute(
        "SELECT price FROM prices WHERE price_type = ? AND price_name LIKE ?",
        [new_price_type, price_name],
    ).fetchone()

    if price:
        return price[0] + (5 if price_type == "bin" else 0)

    # Caso o level requisitado não exista na db:
    price = cur.execute(
        "SELECT price FROM prices WHERE price_type = ? AND price_name LIKE ?",
        [new_price_type, "INDEFINIDO"],
    ).fetchone()

    if price:
        return price[0] + (5 if price_type == "bin" else 0)

    return 12


async def get_person():
  with open("assets/pessoas.json", "r", encoding="utf8") as f:
    r = json.load(f)
    pessoas = r['pessoa']
    q = len(pessoas)
    pessoa = pessoas[randint(0, q-1)]
    cpf = pessoa['cpf']
    nome = pessoa['nome']
    return cpf, nome


def create_mention(user: User, with_id: bool = True) -> str:
    name = f"@{user.username}" if user.username else html.escape(user.first_name)

    mention = f"<a href='tg://user?id={user.id}'>{name}</a>"

    if with_id:
        mention += f" (<code>{user.id}</code>)"

    return mention


@alru_cache
async def search_bin(card_bin: Union[str, int]) -> dict:
    """Pesquisa informações sobre a bin e as retorna em um dict."""

    try:
        print("-$+$+")
        r = await hc.get(
            f"http://194.163.185.17/api/?bin={card_bin}",
        )

        rj = r.json()

        info = {"card_bin": card_bin,"country": rj["pais"] or "INDEFINIDO","vendor": rj["bandeira"] or "INDEFINIDO","card_type": rj["tipo"] or "INDEFINIDO","level": rj["level"] or "INDEFINIDO","bank": rj["banco"] or "INDEFINIDO",}
        return info
    except Exception as e:
        print(e)
        info = {
            "card_bin": card_bin,
            "country": "INDEFINIDO",
            "vendor": "INDEFINIDO",
            "card_type": "INDEFINIDO",
            "level": "INDEFINIDO",
            "bank": "INDEFINIDO",
        }
        return info


def to_hex(dec: float):
    digits = "0123456789ABCDEF"
    x = dec % 16
    rest = dec // 16
    if rest == 0:
        return digits[x]
    return to_hex(rest) + digits[x]


def get_crc16(payload: str):
    crc = 0xFFFF
    for i in range(len(payload)):
        crc ^= ord(payload[i]) << 8
        for j in range(8):
            if (crc & 0x8000) > 0:
                crc = (crc << 1) ^ 0x1021
            else:
                crc = crc << 1
    return to_hex(crc & 0xFFFF).upper()


def create_copy_paste_pix(location: str) -> str:
    # Copy paste sem CRC16
    copy_paste = f"00020126830014br.gov.bcb.pix2561{location}520489995303986540105802BR5921Pagseguro Internet SA6009SAO PAULO62070503***6304"

    return copy_paste + get_crc16(copy_paste)


def lock_user_buy(f: Callable):
    @wraps(f)
    async def lock_user(c: Client, m: CallbackQuery, *args, **kwargs):
        q = cur.execute(
            "SELECT is_action_pending FROM users WHERE id = ?", [m.from_user.id]
        ).fetchone()
        cur.execute(
            "UPDATE users SET is_action_pending = ? WHERE id = ?",
            [True, m.from_user.id],
        )
        if q[0]:
            return await m.answer(
                "Você só pode fazer uma compra/troca por vez. Por favor aguarde seu pedido anterior ser concluído.",
                show_alert=True,
            )
        try:
            return await f(c, m, *args, **kwargs)
        finally:
            cur.execute(
                "UPDATE users SET is_action_pending = ? WHERE id = ?",
                [False, m.from_user.id],
            )

    return lock_user
