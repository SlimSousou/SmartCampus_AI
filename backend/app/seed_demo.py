from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import settings
from .database import create_database_engine, create_session_factory
from .models import Program


DEMO_PROGRAMS = (
    {
        "institution": "IIT",
        "name": "DÉMO — Parcours préparatoire IIT",
        "level": "preparatory",
        "description": "Donnée fictive de démonstration; remplacer par une source officielle avant publication.",
        "duration": None,
    },
    {
        "institution": "IIT",
        "name": "DÉMO — Parcours licence IIT",
        "level": "bachelor",
        "description": "Donnée fictive de démonstration; remplacer par une source officielle avant publication.",
        "duration": None,
    },
    {
        "institution": "IIT",
        "name": "DÉMO — Parcours ingénierie IIT",
        "level": "engineering",
        "description": "Donnée fictive de démonstration; remplacer par une source officielle avant publication.",
        "duration": None,
    },
    {
        "institution": "ISB",
        "name": "DÉMO — Formation ISB",
        "level": "other",
        "description": "Donnée fictive de démonstration; remplacer par une source officielle avant publication.",
        "duration": None,
    },
)


def seed_demo_data(db: Session) -> int:
    inserted = 0
    for data in DEMO_PROGRAMS:
        existing = db.scalar(
            select(Program.id).where(
                Program.institution == data["institution"],
                Program.name == data["name"],
            )
        )
        if existing is None:
            db.add(Program(**data, is_demo=True, is_published=False))
            inserted += 1
    db.commit()
    return inserted


def main() -> None:
    engine = create_database_engine(settings.database_url)
    db = create_session_factory(engine)()
    try:
        inserted = seed_demo_data(db)
        print(f"{inserted} programme(s) fictif(s) ajouté(s); ils restent non publiés.")
    finally:
        db.close()
        engine.dispose()


if __name__ == "__main__":
    main()