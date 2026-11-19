Ajoute dans la méthode `scenario`, juste après la ligne `stored = lambda loc=location: ports.ledgers.load(loc)  # noqa: E731`, les lignes :

```python
        ui.navigator.show_tab(__import__("suivi.adapters.driving.gui.contract.dto", fromlist=["Tab"]).Tab.SYNC)
        ui.sync._not_available()
        self.assertIn("Non disponible", ui.sync._status.get())
```
