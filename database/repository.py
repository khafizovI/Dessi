from dataclasses import dataclass, field
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.models import Admin, Expense, Product, Sale


@dataclass
class ReportData:
    period_label: str
    since: datetime
    until: datetime
    revenue: float = 0
    cost: float = 0
    profit: float = 0
    total_qty: int = 0
    sale_count: int = 0
    expenses: float = 0
    net_profit: float = 0
    expense_items: list[dict] = field(default_factory=list)
    products: list[dict] = field(default_factory=list)
    top_product: dict | None = None
    least_product: dict | None = None
    admins: list[dict] = field(default_factory=list)


class ProductRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        name: str,
        sku: str,
        quantity: int,
        cost_price: float,
        sale_price: float,
        image_file_id: str | None = None,
    ) -> Product:
        product = Product(
            name=name,
            sku=sku.upper(),
            quantity=quantity,
            cost_price=cost_price,
            purchase_price=cost_price,
            sale_price=sale_price,
            category="",
            image_file_id=image_file_id,
        )
        self.session.add(product)
        await self.session.commit()
        await self.session.refresh(product)
        return product

    async def get_by_id(self, product_id: int) -> Product | None:
        result = await self.session.execute(
            select(Product).where(Product.id == product_id, Product.is_active.is_(True))
        )
        return result.scalar_one_or_none()

    async def get_by_sku(self, sku: str) -> Product | None:
        result = await self.session.execute(
            select(Product).where(
                Product.sku == sku.upper(), Product.is_active.is_(True)
            )
        )
        return result.scalar_one_or_none()

    async def get_all(self) -> list[Product]:
        result = await self.session.execute(
            select(Product)
            .where(Product.is_active.is_(True))
            .order_by(Product.name)
        )
        return list(result.scalars().all())

    async def get_low_stock(self, threshold: int) -> list[Product]:
        result = await self.session.execute(
            select(Product)
            .where(Product.is_active.is_(True), Product.quantity <= threshold)
            .order_by(Product.quantity)
        )
        return list(result.scalars().all())

    async def deactivate(self, product_id: int) -> Product | None:
        result = await self.session.execute(
            select(Product).where(Product.id == product_id, Product.is_active.is_(True))
        )
        product = result.scalar_one_or_none()
        if not product:
            return None
        product.is_active = False
        await self.session.commit()
        await self.session.refresh(product)
        return product

    async def update_stock(self, product_id: int, delta: int) -> Product | None:
        product = await self.get_by_id(product_id)
        if not product:
            return None
        product.quantity += delta
        await self.session.commit()
        await self.session.refresh(product)
        return product


class SaleRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    def _active_filter(self, since: datetime, until: datetime):
        return (
            Sale.created_at >= since,
            Sale.created_at < until,
            Sale.is_cancelled.is_(False),
        )

    async def create(
        self,
        product: Product,
        quantity: int,
        sale_price: float,
        admin: Admin | None = None,
    ) -> Sale | None:
        if product.quantity < quantity:
            return None
        sale = Sale(
            product_id=product.id,
            quantity=quantity,
            sale_price=sale_price,
            cost_price=product.cost_price,
            purchase_price=product.cost_price,
            admin_id=admin.id if admin else None,
            admin_name=admin.name if admin else "",
        )
        product.quantity -= quantity
        self.session.add(sale)
        await self.session.commit()
        await self.session.refresh(sale)
        return sale

    async def get_by_id(self, sale_id: int) -> Sale | None:
        result = await self.session.execute(
            select(Sale)
            .options(selectinload(Sale.product))
            .where(Sale.id == sale_id)
        )
        return result.scalar_one_or_none()

    async def get_history(
        self, since: datetime | None = None, limit: int = 30
    ) -> list[Sale]:
        query = (
            select(Sale)
            .options(selectinload(Sale.product))
            .where(Sale.is_cancelled.is_(False))
            .order_by(Sale.created_at.desc())
            .limit(limit)
        )
        if since:
            query = query.where(Sale.created_at >= since)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_recent_for_cancel(self, limit: int = 20) -> list[Sale]:
        result = await self.session.execute(
            select(Sale)
            .options(selectinload(Sale.product))
            .where(Sale.is_cancelled.is_(False))
            .order_by(Sale.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def cancel(self, sale_id: int) -> Sale | None:
        sale = await self.get_by_id(sale_id)
        if not sale or sale.is_cancelled:
            return None
        sale.is_cancelled = True
        sale.cancelled_at = datetime.now()
        if sale.product:
            sale.product.quantity += sale.quantity
        await self.session.commit()
        await self.session.refresh(sale)
        return sale

    async def build_report(
        self, since: datetime, until: datetime, period_label: str
    ) -> ReportData:
        filters = self._active_filter(since, until)

        totals = await self.session.execute(
            select(
                func.count(Sale.id).label("count"),
                func.coalesce(func.sum(Sale.quantity), 0).label("total_qty"),
                func.coalesce(func.sum(Sale.quantity * Sale.sale_price), 0).label(
                    "revenue"
                ),
                func.coalesce(func.sum(Sale.quantity * Sale.cost_price), 0).label(
                    "cost"
                ),
            ).where(*filters)
        )
        row = totals.one()
        revenue = float(row.revenue)
        cost = float(row.cost)
        profit = revenue - cost

        expense_repo = ExpenseRepository(self.session)
        expenses = await expense_repo.get_total_between(since, until)
        expense_list = await expense_repo.get_all_between(since, until)
        expense_items = [
            {
                "description": e.description,
                "amount": e.amount,
                "admin_name": e.admin_name or "",
                "date": e.created_at.strftime("%d.%m.%Y %H:%M"),
            }
            for e in expense_list
        ]

        product_rows = await self.session.execute(
            select(
                Product.name,
                Product.sku,
                func.sum(Sale.quantity).label("qty"),
                func.sum(Sale.quantity * Sale.sale_price).label("revenue"),
                func.sum(Sale.quantity * Sale.cost_price).label("cost"),
            )
            .join(Product, Sale.product_id == Product.id)
            .where(*filters)
            .group_by(Product.id, Product.name, Product.sku)
            .order_by(func.sum(Sale.quantity).desc())
        )
        products = []
        for r in product_rows.all():
            rev = float(r.revenue)
            cst = float(r.cost)
            products.append(
                {
                    "name": r.name,
                    "sku": r.sku,
                    "qty": int(r.qty),
                    "revenue": rev,
                    "cost": cst,
                    "profit": rev - cst,
                }
            )

        top_product = products[0] if products else None
        least_product = products[-1] if products else None

        admin_rows = await self.session.execute(
            select(
                Sale.admin_name,
                func.count(Sale.id).label("count"),
                func.coalesce(func.sum(Sale.quantity), 0).label("qty"),
                func.coalesce(func.sum(Sale.quantity * Sale.sale_price), 0).label(
                    "revenue"
                ),
            )
            .where(*filters)
            .group_by(Sale.admin_name)
            .order_by(func.sum(Sale.quantity * Sale.sale_price).desc())
        )
        admins = [
            {
                "name": r.admin_name or "Noma'lum",
                "count": int(r.count),
                "qty": int(r.qty),
                "revenue": float(r.revenue),
            }
            for r in admin_rows.all()
        ]

        return ReportData(
            period_label=period_label,
            since=since,
            until=until,
            revenue=revenue,
            cost=cost,
            profit=profit,
            total_qty=int(row.total_qty),
            sale_count=int(row.count),
            expenses=expenses,
            net_profit=profit - expenses,
            expense_items=expense_items,
            products=products,
            top_product=top_product,
            least_product=least_product,
            admins=admins,
        )


class ExpenseRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self, description: str, amount: float, admin_name: str = ""
    ) -> Expense:
        expense = Expense(
            description=description, amount=amount, admin_name=admin_name
        )
        self.session.add(expense)
        await self.session.commit()
        await self.session.refresh(expense)
        return expense

    async def get_total_between(self, since: datetime, until: datetime) -> float:
        result = await self.session.execute(
            select(func.coalesce(func.sum(Expense.amount), 0)).where(
                Expense.created_at >= since,
                Expense.created_at < until,
            )
        )
        return float(result.scalar_one())

    async def get_all_between(
        self, since: datetime, until: datetime
    ) -> list[Expense]:
        result = await self.session.execute(
            select(Expense)
            .where(Expense.created_at >= since, Expense.created_at < until)
            .order_by(Expense.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_all(self, limit: int = 100) -> list[Expense]:
        result = await self.session.execute(
            select(Expense).order_by(Expense.created_at.desc()).limit(limit)
        )
        return list(result.scalars().all())


class AdminRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self, telegram_id: int, name: str, is_main: bool = False
    ) -> Admin:
        admin = Admin(telegram_id=telegram_id, name=name, is_main=is_main)
        self.session.add(admin)
        await self.session.commit()
        await self.session.refresh(admin)
        return admin

    async def get_by_id(self, admin_id: int) -> Admin | None:
        result = await self.session.execute(
            select(Admin).where(Admin.id == admin_id)
        )
        return result.scalar_one_or_none()

    async def get_by_telegram_id(self, telegram_id: int) -> Admin | None:
        result = await self.session.execute(
            select(Admin).where(Admin.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()

    async def get_all(self) -> list[Admin]:
        result = await self.session.execute(
            select(Admin).order_by(Admin.name)
        )
        return list(result.scalars().all())

    async def count(self) -> int:
        result = await self.session.execute(select(func.count(Admin.id)))
        return int(result.scalar_one())

    async def delete(self, admin_id: int) -> Admin | None:
        admin = await self.get_by_id(admin_id)
        if not admin:
            return None
        await self.session.delete(admin)
        await self.session.commit()
        return admin


def day_start(dt: datetime | None = None) -> datetime:
    now = dt or datetime.now()
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def day_end(dt: datetime | None = None) -> datetime:
    return day_start(dt) + timedelta(days=1)


def period_range(period: str) -> tuple[datetime, datetime, str]:
    now = datetime.now()
    if period == "today":
        return day_start(now), day_end(now), "📅 Bugungi"
    if period == "yesterday":
        y = now - timedelta(days=1)
        return day_start(y), day_end(y), "📅 Kechagi"
    if period == "weekly":
        start = now - timedelta(days=now.weekday())
        return day_start(start), day_end(now), "📆 Haftalik"
    if period == "monthly":
        start = now.replace(day=1)
        return day_start(start), day_end(now), "🗓 Oylik"
    raise ValueError(f"Unknown period: {period}")


def parse_date(text: str) -> datetime | None:
    text = text.strip()
    for fmt in ("%d.%m.%Y", "%d.%m.%y", "%d/%m/%Y"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None
