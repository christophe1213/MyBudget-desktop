"""Garde-fou d'architecture : la règle de dépendance de l'hexagone est vérifiée automatiquement.

Les dépendances ne vont que vers l'intérieur :
    adaptateurs ──► application ──► domaine
Un import interdit fait échouer ce test, donc l'architecture ne peut pas se dégrader sans qu'on le voie.
"""
import ast
import os
import sys
import unittest

ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "suivi")
STDLIB = set(sys.stdlib_module_names)

# couche -> (préfixes internes autorisés, bibliothèques tierces autorisées)
RULES = {
    "suivi.domain": (("suivi.domain",), ()),
    "suivi.application": (("suivi.domain", "suivi.application"), ()),
    "suivi.adapters.driven": (("suivi.domain", "suivi.application", "suivi.adapters.driven"),
                              ("openpyxl", "sqlmodel", "sqlalchemy", "pydantic")),
    "suivi.adapters.driving": (("suivi.domain", "suivi.application", "suivi.adapters.driving"),
                               ("tkinter", "customtkinter")),
}


def modules():
    for folder, _dirs, files in os.walk(ROOT):
        for name in files:
            if name.endswith(".py"):
                path = os.path.join(folder, name)
                relative = os.path.relpath(path, os.path.dirname(ROOT))[:-3].replace(os.sep, ".")
                yield relative, path


def imports(module, path):
    """Noms de modules importés (absolus) par un fichier."""
    package = module.rsplit(".", 1)[0] if not module.endswith(".__init__") else module[:-9]
    found = []
    with open(path, encoding="utf-8") as f:
        tree = ast.parse(f.read())
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found += [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                base = package.split(".")[:len(package.split(".")) - node.level + 1]
                found.append(".".join(base + ([node.module] if node.module else [])))
            else:
                found.append(node.module)
    return found


class ArchitectureTest(unittest.TestCase):
    def violations(self, check):
        return [f"{module} -> {target}" for module, path in modules() for target in imports(module, path)
                if check(module, target)]

    def test_regle_de_dependance_par_couche(self):
        def forbidden(module, target):
            top = target.split(".")[0]
            for layer, (internal, third_party) in RULES.items():
                if module.startswith(layer + ".") or module == layer:
                    if top == "suivi":
                        return not target.startswith(internal)
                    return top not in STDLIB and top not in third_party
            return False
        self.assertEqual(self.violations(forbidden), [])

    def test_bibliotheques_confinees_a_leur_adaptateur(self):
        def forbidden(module, target):
            top = target.split(".")[0]
            if top == "tkinter":
                return not module.startswith(("suivi.adapters.driving.gui.tk", "suivi.adapters.driving.gui.ctk"))
            if top == "customtkinter":
                return not module.startswith("suivi.adapters.driving.gui.ctk")
            if top in ("sqlmodel", "sqlalchemy", "pydantic"):   # ORM : confiné à l'adaptateur des comptes
                return not module.startswith("suivi.adapters.driven.sqlmodel_auth")
            if top in ("openpyxl", "sqlite3"):
                return not module.startswith("suivi.adapters.driven")
            return top in ("pandas", "numpy")
        self.assertEqual(self.violations(forbidden), [])

    def test_les_controleurs_ne_voient_que_les_ports_entrants(self):
        def forbidden(module, target):
            if not module.startswith("suivi.adapters.driving.gui.controllers"):
                return False
            return target.startswith(("suivi.application.use_cases", "suivi.application.session",
                                      "suivi.application.ports.outbound", "suivi.adapters.driven"))
        self.assertEqual(self.violations(forbidden), [])

    def test_les_deux_interfaces_sont_independantes(self):
        """tk/ et ctk/ implémentent les mêmes contrats sans jamais s'importer l'une l'autre."""
        def forbidden(module, target):
            for mine, other in (("tk", "ctk"), ("ctk", "tk")):
                if module.startswith(f"suivi.adapters.driving.gui.{mine}.") and target.startswith(
                        f"suivi.adapters.driving.gui.{other}"):
                    return True
            return False
        self.assertEqual(self.violations(forbidden), [])

    def test_les_contrats_et_controleurs_ignorent_les_bibliotheques_graphiques(self):
        def forbidden(module, target):
            neutral = module.startswith(("suivi.adapters.driving.gui.contract", "suivi.adapters.driving.gui.controllers")) \
                or module in ("suivi.adapters.driving.gui.chart_painter", "suivi.adapters.driving.gui.dashboard_painter",
                              "suivi.adapters.driving.gui.formatting",
                              "suivi.adapters.driving.gui.parsing", "suivi.adapters.driving.gui.view_support")
            return neutral and (target.startswith(("tkinter", "customtkinter"))
                                or target.startswith(("suivi.adapters.driving.gui.tk", "suivi.adapters.driving.gui.ctk")))
        self.assertEqual(self.violations(forbidden), [])

    def test_seule_la_racine_de_composition_connait_les_classes_concretes(self):
        def forbidden(module, target):
            if module in ("suivi.bootstrap",):
                return False
            return target.startswith("suivi.application.use_cases") and not module.startswith(
                "suivi.application.use_cases")
        self.assertEqual(self.violations(forbidden), [])


if __name__ == "__main__":
    unittest.main()
