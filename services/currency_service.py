
import aiohttp
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class CurrencyConverter:
    BASE_URL = "https://api.exchangerate-api.com/v4/latest/USD"
    
    @staticmethod
    async def get_rate(to_currency: str) -> Optional[float]:
        """Get conversion rate from USD to target currency"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(CurrencyConverter.BASE_URL) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data['rates'].get(to_currency.upper())
            return None
        except Exception as e:
            logger.error(f"Failed to get currency rate: {e}")
            return None
    
    @staticmethod
    async def convert_price(price: float, to_currency: str) -> Optional[float]:
        """Convert price from USD to target currency"""
        rate = await CurrencyConverter.get_rate(to_currency)
        if rate:
            return price * rate
        return None
