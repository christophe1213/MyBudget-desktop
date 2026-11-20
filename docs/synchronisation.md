# Synchronisation (préparation)

L'onglet **Synchronisation** démarre un petit serveur HTTP local (`suivi/adapters/driving/sync_server.py`) et affiche
un QR code contenant son adresse. C'est un adaptateur *pilotant* : un autre appareil du même réseau pourra, plus tard,
commander l'application à travers lui (via les ports entrants).

Pour l'instant il expose seulement :

- `/health` : état du serveur (JSON) ;
- `/qr.png` : le QR code de l'adresse (nécessite `qrcode[pil]`) ;
- `/` : une page de test.

Aucune donnée financière n'est encore envoyée ni reçue. Le serveur écoute sur toutes les interfaces réseau
(`0.0.0.0`) tant qu'il est démarré : ne l'activez que sur un réseau de confiance.

Dépendances : `pip install qrcode[pil]` (le QR code est facultatif, le reste de l'application fonctionne sans).
