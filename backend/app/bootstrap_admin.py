from getpass import getpass

from sqlalchemy import select

from . import models
from .config import settings
from .database import Base, create_database_engine, create_session_factory
from .models import Role, User
from .security import hash_password


def main() -> None:
    engine = create_database_engine(settings.database_url)
    if settings.auto_create_tables:
        Base.metadata.create_all(bind=engine)
    session_factory = create_session_factory(engine)
    db = session_factory()
    try:
        if db.scalar(select(User.id).where(User.role == Role.ADMIN.value, User.is_active.is_(True))) is not None:
            raise SystemExit("Un administrateur actif existe déjà; utiliser l'API admin pour gérer les rôles.")
        email = input("Adresse email du premier administrateur : ").strip().lower()
        password = getpass("Mot de passe (12 caractères minimum) : ")
        confirmation = getpass("Confirmer le mot de passe : ")
        if len(password) < 12 or password != confirmation:
            raise SystemExit("Mot de passe trop court ou confirmation incorrecte.")
        if db.scalar(select(User.id).where(User.email == email)) is not None:
            raise SystemExit("Cette adresse email existe déjà.")
        db.add(
            User(
                email=email,
                full_name="Administrateur initial",
                password_hash=hash_password(password),
                role=Role.ADMIN.value,
            )
        )
        db.commit()
        print("Compte administrateur créé. Supprimer l'accès opérateur après le bootstrap.")
    finally:
        db.close()
        engine.dispose()


if __name__ == "__main__":
    main()