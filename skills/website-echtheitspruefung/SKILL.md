---
name: website-echtheitspruefung
description: Prüft, ob eine Webseite oder Domain echt ist oder ein Fake — Fakeshop, Job-/Projekt-Scam, Impressumsdiebstahl, Phishing. Wertet Domain-Alter und -Inhaber, TLS-Zertifikate, Wayback-Historie, Mail-DNS, Impressum gegen Handelsregister und VIES sowie Reputation und Warnlisten aus und gibt ein Ampel-Urteil mit Belegen. Nutzen, wenn eine URL auf Seriosität geprüft werden soll, z. B. "ist die Seite echt?", "ist das seriös?", "Fakeshop?", "ist das Phishing?", "ist das ein Scam?", "gehört die Domain wirklich zu Firma X?", bei verdächtigen Job- oder Projektangeboten oder "is this site legit?".
---

# Website-Echtheitsprüfung

Ziel: Einschätzung, ob eine Webseite zu dem Unternehmen gehört, das sie vorgibt zu sein,
oder ob es ein Fake ist (Fakeshop, Job-/Projekt-Scam, Impressumsdiebstahl, Phishing).
Ergebnis immer als Ampel mit Belegen — nie als Gewissheit ausgeben, wenn sie nicht belegt
ist.

## Sicherheitsregeln

- Nur lesen: keine Formulare absenden, nichts herunterladen, keine Kontaktaufnahme, keine
  Daten eingeben.
- Zum Rendern einen isolierten Browser bevorzugen. Den echten Browser des Users mit
  seinen Logins nur nutzen, wenn kein anderer verfügbar ist, und dann in einem neuen Tab.
- URLs, die persönliche Tokens oder Tracking-Parameter enthalten (Bewerbungs-, Einladungs-
  oder Reset-Links), nie bei urlscan.io, VirusTotal o. ä. einreichen — diese Dienste
  veröffentlichen eingereichte URLs. Nur die nackte Domain prüfen; bei urlscan.io
  "Unlisted" oder "Private" wählen.

## Ablauf

Alle unabhängigen Abfragen parallel im selben Turn starten.

### 1. Seite lesen

- Seite mit dem Fetch-Tool abrufen. Liefert sie nur Meta-Daten (typisch bei SPAs mit
  `#/`-Routen), im Browser rendern und den Text lesen: Startseite, Impressum, Datenschutz,
  Kontakt, Team.
- Generator-Spuren notieren: og:image von bolt.new, Lovable, v0, Framer-Templates,
  Platzhaltertexte, Lorem ipsum, kaputte Links, generische Stock- oder KI-Porträts.
- Notieren: Firmenname, Rechtsform, Adresse, HRB + Registergericht, USt-IdNr.,
  Geschäftsführer, Telefon, E-Mail-Domain, angebotene Leistung.

### 2. Domain

- WHOIS: `https://www.whois.com/whois/<domain>` (RDAP der Registries blockt oft per
  robots.txt). Erfassen: Registrierungsdatum, Registrar, Privacy-Dienst, Nameserver,
  letzte Änderung.
- `.de`-Domains: Die DENIC veröffentlicht kein Registrierungsdatum und keinen Inhaber.
  Das Alter dann über erstes TLS-Zertifikat und ersten Wayback-Snapshot schätzen und im
  Bericht als Schätzung kennzeichnen.
- Bewertung Alter: unter 32 Tage = rot, unter 90 Tage = gelb. Eine neue Domain allein ist
  kein Beweis (echte Neugründungen), aber zusammen mit "seit Jahren etablierte Firma" ein
  starkes Signal.
- Erstes TLS-Zertifikat: `https://crt.sh/?q=<domain>` (Datum ≈ Go-Live, weitere
  Subdomains).
- Erster Wayback-Snapshot:
  `https://web.archive.org/cdx/search/cdx?url=<domain>&limit=1&output=json` (aufsteigend
  sortiert, erster Treffer = ältester Snapshot). Nie archiviert + angeblich etablierte
  Firma = Warnsignal.
- Lookalike: Weicht die Domain von der offiziellen Domain der Firma ab (Bindestrich,
  Zusatz wie -it, -solutions, andere TLD)? Offizielle Domain der Firma per Websuche
  ermitteln.
- Mail-Infrastruktur über `https://dns.google/resolve?name=<name>&type=<typ>`:
  MX und SPF (TXT) auf `<domain>`, DMARC (TXT) auf `_dmarc.<domain>`. Keine MX bei einer
  Firma, die per Mail kommuniziert, oder Mails von Freemail-Adressen = Warnsignal.

### 3. Impressum gegen Register prüfen

- Handelsregister: Firmenname + HRB suchen (northdata.de, webvalid.de,
  Creditreform-Firmeneintrag; northdata liefert oft 429, dann Websuche mit Name + HRB;
  offiziell: handelsregister.de).
- Abgleichen: Name, Sitz, Adresse, Geschäftsführer, HRB exakt identisch? Passt der
  Unternehmensgegenstand zur Seite?
- Muster Impressumsdiebstahl: Die echte Firma existiert, hat aber eine andere offizielle
  Domain oder Marke; die neue Domain wird nirgends von der Firma selbst erwähnt.
- Muster Mantel-/Firmenübernahme: kurz zurückliegende Sitzverlegungen und
  Geschäftsführerwechsel, danach neue Webpräsenz in anderer Branche.
- USt-IdNr. über VIES prüfen (`https://ec.europa.eu/taxation_customs/vies/`, sonst Link
  für den User). Für deutsche Nummern liefert VIES nur gültig/ungültig, keinen Namen —
  ein Namensabgleich ist damit nicht möglich.
- Adresse: Existiert sie, ist es ein virtuelles Büro oder Coworking, passt sie zum
  Register?

### 4. Reputation und Warnlisten

- Websuche: "<Domain>", "<Firmenname> Betrug", "<Firmenname> Erfahrungen",
  "<Firmenname> scam".
- Watchlist Internet (watchlist-internet.at) nach Domain und Firma durchsuchen.
- Links für die manuelle Prüfung mitgeben, wenn nicht abrufbar: Fakeshop-Finder der
  Verbraucherzentrale, Google Transparency Report (Safe Browsing), VirusTotal,
  urlscan.io, ScamAdviser.
- Personen auf der Seite: Name + Firma auf LinkedIn/Xing suchen; dem User eine
  Rückwärts-Bildersuche der Fotos empfehlen.

### 5. Kontextbezogene Warnzeichen

- Job- oder Projektangebot: Video-Ident, Kontoeröffnung im eigenen Namen, Ausweiskopie
  vor Vertragsschluss, Vorauszahlungen, Kauf von Unterlagen, ungewöhnlich hohe
  Vergütung, Kommunikation nur per Messenger.
- Shop: nur Vorkasse, unrealistische Preise, fehlende Widerrufsbelehrung.

## Ausgabe (kurz, Deutsch)

1. Urteil als Ampel in einem Satz: Rot (sehr wahrscheinlich Fake), Gelb (verdächtig,
   unbelegt), Grün (keine Auffälligkeiten).
2. Belege als knappe Liste: Domain (Alter, Registrar, Privacy), Seite (Generator,
   Impressum), Register (Abgleich), Reputation.
3. Was nicht geprüft werden konnte und warum.
4. Konkreter nächster Schritt, z. B. Firma über ihre offizielle Domain oder die
   Telefonnummer aus dem Register kontaktieren, keine Daten senden, ggf. an Watchlist
   Internet melden.
5. Quellen als Liste.

Keine Behauptung, dass eine konkrete Person hinter dem Fake steckt. Inhaber hinter
Privacy-Diensten als unbekannt ausweisen.
