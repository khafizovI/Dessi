from aiogram import Router

from bot.handlers import admins, history, products, reports, sales, start

router = Router()
router.include_router(start.router)
router.include_router(products.router)
router.include_router(sales.router)
router.include_router(reports.router)
router.include_router(history.router)
router.include_router(admins.router)
