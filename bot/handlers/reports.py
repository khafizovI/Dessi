from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import FSInputFile, Message

from bot.keyboards.menus import CANCEL_KB, REPORT_KB
from bot.states.forms import ReportStates
from database.repository import (
    SaleRepository,
    day_end,
    day_start,
    parse_date,
    period_range,
)
from database.session import async_session
from services.export import export_excel, export_pdf
from services.report_builder import build_report_text

router = Router()

_last_report: dict[int, object] = {}


async def _show_report(message: Message, since, until, label: str):
    async with async_session() as session:
        repo = SaleRepository(session)
        report = await repo.build_report(since, until, label)

    _last_report[message.from_user.id] = report
    text = build_report_text(report)

    if len(text) > 4000:
        await message.answer(text[:4000], parse_mode="HTML", reply_markup=REPORT_KB)
        await message.answer(text[4000:], parse_mode="HTML")
    else:
        await message.answer(text, parse_mode="HTML", reply_markup=REPORT_KB)


@router.message(F.text == "📊 Hisobot")
async def report_menu(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "📊 <b>Hisobot</b>\n\n📅 Davrni tanlang yoki eksport qiling:",
        reply_markup=REPORT_KB,
        parse_mode="HTML",
    )


@router.message(F.text == "📅 Bugun")
async def report_today(message: Message):
    since, until, label = period_range("today")
    await _show_report(message, since, until, label)


@router.message(F.text == "📅 Kecha")
async def report_yesterday(message: Message):
    since, until, label = period_range("yesterday")
    await _show_report(message, since, until, label)


@router.message(F.text == "📆 Haftalik")
async def report_weekly(message: Message):
    since, until, label = period_range("weekly")
    await _show_report(message, since, until, label)


@router.message(F.text == "🗓 Oylik")
async def report_monthly(message: Message):
    since, until, label = period_range("monthly")
    await _show_report(message, since, until, label)


@router.message(F.text == "📆 Sana oralig'i")
async def report_custom_start(message: Message, state: FSMContext):
    await state.set_state(ReportStates.date_from)
    await message.answer(
        "📆 <b>Boshlanish sanasini kiriting:</b>\n"
        "<i>Format: 01.07.2026</i>",
        reply_markup=CANCEL_KB,
        parse_mode="HTML",
    )


@router.message(ReportStates.date_from)
async def report_date_from(message: Message, state: FSMContext):
    dt = parse_date(message.text)
    if not dt:
        await message.answer("⚠️ Noto'g'ri sana!\n📆 Masalan: 01.07.2026")
        return
    await state.update_data(date_from=dt.isoformat())
    await state.set_state(ReportStates.date_to)
    await message.answer(
        "📆 <b>Tugash sanasini kiriting:</b>\n"
        "<i>Format: 15.07.2026</i>",
        reply_markup=CANCEL_KB,
        parse_mode="HTML",
    )


@router.message(ReportStates.date_to)
async def report_date_to(message: Message, state: FSMContext):
    dt = parse_date(message.text)
    if not dt:
        await message.answer("⚠️ Noto'g'ri sana!\n📆 Masalan: 15.07.2026")
        return

    from datetime import datetime

    data = await state.get_data()
    since = datetime.fromisoformat(data["date_from"])
    until = day_end(dt)

    if since >= until:
        await message.answer("⚠️ Boshlanish sanasi tugash sanasidan oldin bo'lishi kerak!")
        return

    await state.clear()
    label = f"📆 {since.strftime('%d.%m.%Y')} — {dt.strftime('%d.%m.%Y')}"
    await _show_report(message, since, until, label)


@router.message(F.text == "📄 Excel")
async def export_xlsx(message: Message):
    report = _last_report.get(message.from_user.id)
    if not report:
        await message.answer(
            "⚠️ Avval hisobot davrini tanlang!\n📊 Bugun, Haftalik yoki Oylik.",
            reply_markup=REPORT_KB,
        )
        return
    filepath = export_excel(report)
    await message.answer_document(
        FSInputFile(filepath),
        caption="📄 Hisobot.xlsx",
        reply_markup=REPORT_KB,
    )


@router.message(F.text == "📄 PDF")
async def export_pdf_file(message: Message):
    report = _last_report.get(message.from_user.id)
    if not report:
        await message.answer(
            "⚠️ Avval hisobot davrini tanlang!\n📊 Bugun, Haftalik yoki Oylik.",
            reply_markup=REPORT_KB,
        )
        return
    filepath = export_pdf(report)
    await message.answer_document(
        FSInputFile(filepath),
        caption="📄 Oylik hisobot.pdf",
        reply_markup=REPORT_KB,
    )
