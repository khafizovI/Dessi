from database.repository import ReportData


def fmt_money(value: float) -> str:
    return f"{value:,.0f}"


def build_report_text(report: ReportData) -> str:
    lines = [
        f"{report.period_label} <b>hisobot</b>\n",
        f"💰 Jami tushum: <b>{fmt_money(report.revenue)}</b> so'm",
        f"💵 Jami dastmoya: <b>{fmt_money(report.cost)}</b> so'm",
        f"📈 Sotuv foydasi: <b>{fmt_money(report.profit)}</b> so'm",
        f"📝 Xarajatlar: <b>{fmt_money(report.expenses)}</b> so'm",
        f"✨ Sof foyda: <b>{fmt_money(report.net_profit)}</b> so'm",
        f"📦 Sotilgan mahsulot: <b>{report.total_qty}</b> dona",
        f"🛒 Sotuvlar soni: <b>{report.sale_count}</b> ta",
    ]

    if report.top_product:
        t = report.top_product
        lines.append(
            f"\n🏆 <b>Eng ko'p sotilgan:</b> {t['name']} — {t['qty']} ta"
        )
    if report.least_product and len(report.products) > 1:
        l = report.least_product
        lines.append(
            f"📉 <b>Eng kam sotilgan:</b> {l['name']} — {l['qty']} ta"
        )

    if report.admins:
        lines.append("\n👤 <b>Sotuvchilar:</b>")
        for a in report.admins:
            lines.append(
                f"  • <b>{a['name']}</b>\n"
                f"    🛒 {a['count']} ta sotuv | "
                f"📦 {a['qty']} dona | "
                f"💰 {fmt_money(a['revenue'])} so'm"
            )

    if report.products:
        lines.append("\n📋 <b>Mahsulotlar bo'yicha:</b>")
        for p in report.products:
            lines.append(
                f"  👕 <b>{p['name']}</b> ({p['sku']})\n"
                f"     🔢 {p['qty']} ta | "
                f"💰 {fmt_money(p['revenue'])} | "
                f"💵 {fmt_money(p['cost'])} | "
                f"✨ {fmt_money(p['profit'])}"
            )
    else:
        lines.append("\n📭 Bu davrda sotuvlar yo'q.")

    return "\n".join(lines)
