from datetime import datetime

from sqlalchemy import String, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ServiceRequest(Base):
    """The intake pipeline: a vertical asks the AI team to build something.
    A signed BRD is compulsory before this can be submitted."""

    __tablename__ = "service_requests"

    id: Mapped[int] = mapped_column(primary_key=True)

    vertical_id: Mapped[int] = mapped_column(ForeignKey("verticals.id"))
    vertical = relationship("Vertical")

    requestor_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    requestor = relationship("User", foreign_keys=[requestor_id])

    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Compulsory - the submit endpoint refuses without this being set.
    brd_file_path: Mapped[str] = mapped_column(String(500))

    # submitted -> under_review -> approved | rejected | on_hold
    status: Mapped[str] = mapped_column(String(20), default="submitted")

    reviewed_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    reviewed_by = relationship("User", foreign_keys=[reviewed_by_id])
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Extra people the REQUESTOR chose to keep in the loop when they filed
    # this. Stored as a JSON list of addresses so one choice follows the
    # request through all three of its emails - submitted, reviewed, delivered
    # - instead of being retyped at each step. The vertical head and the AI
    # team are added by the app and are not in here.
    extra_to: Mapped[str | None] = mapped_column(Text, nullable=True)
    extra_cc: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
