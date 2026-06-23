"""
Vervang gedachtestreepjes (em-dash — / en-dash –) door komma's in alle
bewerkbare content. Robin heeft een hekel aan die streepjes. Idempotent en
veilig om bij elke deploy te draaien (na vervanging zijn er geen streepjes meer).

    python manage.py normalize_dashes            # pas toe
    python manage.py normalize_dashes --dry-run  # toon alleen wat zou wijzigen
"""
from django.apps import apps
from django.core.management.base import BaseCommand
from django.db import models


def fix(text):
    """' — ' / ' – ' -> ', '; losse —/– -> ','. Laat gewone koppeltekens (-) staan."""
    if not text or ("—" not in text and "–" not in text):
        return text
    out = text
    for dash in ("—", "–"):
        out = out.replace(" " + dash + " ", ", ")
        out = out.replace(" " + dash, ",")
        out = out.replace(dash + " ", ", ")
        out = out.replace(dash, ",")
    return out


class Command(BaseCommand):
    help = "Vervang gedachtestreepjes door komma's in alle content (idempotent)."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **opts):
        dry = opts["dry_run"]
        total_fields = 0
        for model in apps.get_app_config("core").get_models():
            fields = [f for f in model._meta.get_fields()
                      if isinstance(f, (models.CharField, models.TextField))
                      and not getattr(f, "choices", None)]
            if not fields:
                continue
            for obj in model.objects.all():
                changed = []
                for f in fields:
                    val = getattr(obj, f.name, None)
                    if not isinstance(val, str):
                        continue
                    new = fix(val)
                    if new != val:
                        setattr(obj, f.name, new)
                        changed.append(f.name)
                if changed:
                    total_fields += len(changed)
                    if dry:
                        self.stdout.write(f"  {model.__name__}#{obj.pk}: {', '.join(changed)}")
                    else:
                        obj.save(update_fields=changed)
        verb = "zou wijzigen" if dry else "gewijzigd"
        self.stdout.write(self.style.SUCCESS(f"normalize_dashes: {total_fields} velden {verb}."))
