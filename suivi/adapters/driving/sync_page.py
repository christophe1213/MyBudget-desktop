"""Page servie à la racine du serveur : un petit client WebSocket de TEST, ouvert en flashant le QR code.

Elle montre la connexion, permet de demander les données du PC (puis de les télécharger) et d'envoyer un
fichier .json au PC. Elle répond aussi aux demandes du PC avec le fichier choisi.
Tout le texte reçu est affiché avec `textContent` (jamais `innerHTML`).
"""

PAGE = r"""<!doctype html>
<html lang="fr">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Repère synchronisation</title>
<style>
  body { font-family: system-ui, sans-serif; max-width: 40rem; margin: 1.5rem auto; padding: 0 1rem; }
  button { padding: .6rem 1rem; margin: .25rem 0; }
  pre { background: #f3f6f4; padding: .6rem; white-space: pre-wrap; }
</style>
<h1>Repère synchronisation</h1>
<p id="state">Non connecté.</p>
<p><button id="pull" disabled>Récupérer les données du PC</button></p>
<p><label>Données à envoyer au PC (fichier .json)<br><input type="file" id="file" accept=".json,application/json"></label></p>
<p><button id="push" disabled>Envoyer au PC</button></p>
<p id="download"></p>
<pre id="log"></pre>
<script>
"use strict";
const token = new URLSearchParams(location.search).get("token");
const $ = (id) => document.getElementById(id);
let socket = null, chosen = null;

function note(text) {
  $("log").textContent = new Date().toLocaleTimeString() + "  " + text + "\n" + $("log").textContent;
}
function send(message) {
  if (socket && socket.readyState === WebSocket.OPEN) socket.send(JSON.stringify(message));
}
function summary(payload) {
  const wallets = payload && Array.isArray(payload.wallets) ? payload.wallets : [];
  const count = wallets.reduce((sum, w) => sum + (Array.isArray(w.transactions) ? w.transactions.length : 0), 0);
  return wallets.length + " portefeuille(s), " + count + " transaction(s)";
}
function offerDownload(payload) {
  const link = document.createElement("a");
  link.href = URL.createObjectURL(new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" }));
  link.download = "repere.json";
  link.textContent = "Télécharger repere.json";
  $("download").replaceChildren(link);
}
function connect() {
  if (!token) { $("state").textContent = "Ouvrez cette page en flashant le QR code de l'application."; return; }
  const scheme = location.protocol === "https:" ? "wss://" : "ws://";
  socket = new WebSocket(scheme + location.host + "/ws?token=" + encodeURIComponent(token));
  socket.onopen = () => { $("state").textContent = "Connecté au PC."; $("pull").disabled = $("push").disabled = false; };
  socket.onclose = () => { $("state").textContent = "Connexion fermée."; $("pull").disabled = $("push").disabled = true; };
  socket.onmessage = (event) => {
    let message;
    try { message = JSON.parse(event.data); } catch (e) { note("Message illisible."); return; }
    if (message.type === "data" && message.payload) {
      note("Reçu du PC : " + summary(message.payload));
      offerDownload(message.payload);
    } else if (message.type === "request") {
      if (chosen) { send({ type: "data", payload: chosen }); note("Données envoyées au PC (demande du PC)."); }
      else send({ type: "error", message: "Aucun fichier choisi sur cet appareil." });
    } else if (message.type === "ack" || message.type === "error") {
      note(message.message || message.type);
    }
  };
}
$("pull").onclick = () => send({ type: "request" });
$("push").onclick = () => {
  if (!chosen) { note("Choisissez d'abord un fichier .json."); return; }
  send({ type: "data", payload: chosen });
  note("Données envoyées au PC : " + summary(chosen));
};
$("file").onchange = async (event) => {
  const file = event.target.files[0];
  if (!file) return;
  try { chosen = JSON.parse(await file.text()); note("Fichier prêt : " + summary(chosen)); }
  catch (e) { chosen = null; note("Ce fichier n'est pas un JSON valide."); }
};
connect();
</script>
</html>
"""
