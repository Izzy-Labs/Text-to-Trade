import json
import random

from aiogram import Bot
from psycopg2 import connect
from aioredis import Redis
from solana.rpc.async_api import AsyncClient

from bot.misc.utils import get_token_address
from bot.locales import get_text
from bot import keyboards


class Transactions:
    rpc_client: AsyncClient
    bot_client: Bot
    pg_conn: connect
    redis_conn: Redis

    async def _generate_random_task_id(self, user_id: int) -> str:
        """
        Generate random task id.
        :param user_id:
        :return:
        """

        suffix = random.randint(100000, 999999)
        task_id = f"{user_id}:{suffix}"

        if await self.redis_conn.hexists("tasks", task_id):
            return await self._generate_random_task_id(user_id)
        else:
            return task_id

    async def swap(
            self,
            user_id: int,
            user_address: str,
            first_token_name: str,
            second_token_name: str,
            amount: float,
            settlement_token: str,
    ) -> [str, str]:
        """
        Swap tokens.
        :param user_id: int
        :param user_address: str
        :param first_token_name: str
        :param second_token_name: str
        :param amount: float
        :param settlement_token: str
        :return: type of function, transaction arguments
        """

        first_token_address = get_token_address(first_token_name)
        second_token_address = get_token_address(second_token_name)

        if settlement_token == first_token_name:
            first_token_amount = amount
            second_token_amount = 0
        elif settlement_token == second_token_name:
            first_token_amount = 0
            second_token_amount = amount
        else:
            raise ValueError('Wrong settlement token address!')

        tx_data = {
            'function': 'swap',
            'params': {
                'user_id': user_id,
                'user_address': user_address,
                'first_token_address': first_token_address,
                'first_token_amount': first_token_amount,
                'second_token_address': second_token_address,
                'second_token_amount': second_token_amount,
            }
        }

        task_id = await self._generate_random_task_id(user_id)
        await self.redis_conn.hset(name="tasks", key=task_id, value=json.dumps(tx_data))
        keyboard = keyboards.confirm_transaction(task_id)

        message = get_text(
            msgid='confirm swap',
            language='us',
            token_amount_1='X' if first_token_amount == 0 else first_token_amount,
            token_name_1=first_token_name,
            token_amount_2='X' if second_token_amount == 0 else second_token_amount,
            token_name_2=second_token_name,
        )

        await self.bot_client.send_message(
            chat_id=user_id,
            text=message,
            reply_markup=keyboard
        )

        return 'transaction', tx_data