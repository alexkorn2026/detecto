# Kritische Logdaten und typische Findings

Dieses Dokument beschreibt besonders kritische Informationen in Logdateien. Die Reihenfolge orientiert sich an `/Users/alexanderkornbrust/Documents/Claude/Projects/Butterfly/kritische_logdaten_risikostufen.csv`.

Alle Beispiel-Findings sind fiktiv und fuer Test-, Demo- und Dokumentationszwecke gedacht.

## 1. Passwoerter in Klartext

**Risikostufe:** sehr hoch

**Beschreibung:** Klartext-Passwoerter sind einer der kritischsten Funde in Logdateien. Bereits ein einzelner Treffer kann zur unmittelbaren Kompromittierung von Benutzerkonten, Admin-Zugaengen oder technischen Service-Accounts fuehren.

**20 typische Findings:**

1. `password=Sommer2026!`
2. `passwd=Winter#2025`
3. `userPassword=Start1234`
4. `login failed for user admin with password Admin123!`
5. `resetPassword payload: {"newPassword":"Berlin2026!"}`
6. `db.password=oracleDev!99`
7. `smtpPassword=MailRelay#7`
8. `proxy.password=Forward!234`
9. `technicalUserPassword=BatchRun$55`
10. `credential update: password -> Produktiv!1`
11. `received secret field password='Test12345'`
12. `Password check for user root: Root#Secure9`
13. `bindPassword=ldapSync!2026`
14. `api login request body {"password":"meinPasswort1!"}`
15. `initial password generated: Welcome123!`
16. `service account password is svcImport#88`
17. `auth payload included cleartext password Kundenportal!2`
18. `pw=Geheim123!`
19. `kennwort=ProjektStart2026`
20. `temporary password for jdoe: Temp!4567`

## 2. API-Keys

**Risikostufe:** sehr hoch

**Beschreibung:** API-Keys ermoeglichen oft direkten Zugriff auf SaaS-Dienste, Cloud-Ressourcen oder interne Schnittstellen. Geloggte Keys koennen automatisiert missbraucht und nur schwer vollstaendig zurueckgerufen werden.

**20 typische Findings:**

1. `apiKey=sk_live_1234567890abcdef`
2. `x-api-key: 4f9d2b71c8e34f55a1ab90de7744cc12`
3. `GoogleMapsApiKey=AIzaSyDExampleKey987654321`
4. `Stripe key loaded: sk_test_a1b2c3d4e5f6`
5. `API_KEY=prod-key-7788-xyza-9911`
6. `request header X-API-KEY=9ab3e45f-1b6a-47c4-9f9c-8ab234f0d111`
7. `mailgun.api.key=key-12ab34cd56ef78gh90`
8. `apikey leaked in debug output: SG.abcdEFGHijklMNOP`
9. `weatherServiceKey=ws-prod-44-9988-ABCD`
10. `maps key validation failed for AIzaTestKeyOnly999`
11. `partnerApiKey=partner_live_873462`
12. `sending request with api_key=internal-bridge-2026-01`
13. `configured API access key: AK-test-778899`
14. `api-key param=mobile-app-key-01-prod`
15. `search backend credential apiKey: searchSecret889`
16. `billing connector key=bill-prod-xy-445566`
17. `vault export included apiKey "ops-reader-7744"`
18. `loaded apikey from env: DATAHUB_KEY_99881`
19. `service api key mismatch for key prod_sync_112233`
20. `debug dump: {"apiKey":"customer-demo-key-7"}` 

## 3. Access Tokens

**Risikostufe:** sehr hoch

**Beschreibung:** Access Tokens repraesentieren bereits autorisierte Sitzungen oder Berechtigungen. Ein abgeflossenes Token kann direkten Zugriff auf APIs und Benutzerkontexte geben, bis es ablaeuft oder widerrufen wird.

**20 typische Findings:**

1. `access_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.acc01.sig01`
2. `Authorization: Bearer ya29.a0AfH6SMAExample01`
3. `oauth access token issued: at_live_998877`
4. `received accessToken 8d4f1f72-93e3-4d7c-a5c4-0d99123ab451`
5. `token response {"access_token":"gho_abcd1234token"}`
6. `cached access token for user 4711: tok_prod_f83a11`
7. `Graph token=EwBoA8l6BAAUExample`
8. `Bearer token leaked in request log: mF_9.B5f-4.1JqM`
9. `accessToken=sl.eyJraWQiOiJrMSJ9.payload.sig`
10. `downstream call with token at-dev-334455`
11. `token introspection failed for access token tkn_9988_prod`
12. `session bootstrap returned access_token=cms-acc-778899`
13. `forwarded bearer=service-token-abc-123`
14. `oidc access token stored: oidc_at_987654`
15. `Access token refresh skipped, current token=prodBearer7788`
16. `debug security context: accessToken=mobileUser-8877`
17. `outgoing auth header Bearer svc-at-332211`
18. `token cache hit: access_token "portal-at-9911"`
19. `api gateway accepted token jwt-at-55-xy`
20. `trace: user access_token=acc_demo_20260411`

## 4. Refresh Tokens

**Risikostufe:** sehr hoch

**Beschreibung:** Refresh Tokens sind besonders sensibel, weil sie oft laenger gueltig sind als Access Tokens und neue Access Tokens ausstellen koennen. Ein Leak erhoeht die Persistenz eines Angriffs erheblich.

**20 typische Findings:**

1. `refresh_token=0.AXEAExampleRefresh001`
2. `oauth response {"refresh_token":"rt_live_667788"}`
3. `stored refreshToken=9c7d13e4-441e-47f2-9bc0-0a0f123456aa`
4. `token endpoint issued refresh token rt_prod_12345`
5. `refreshToken=def50200aabbccdd001122`
6. `cache entry refresh_token "portal-refresh-7788"`
7. `mobile login returned refresh token mob_rt_8899`
8. `updating session with refreshToken=sl.rt.eyJ...`
9. `OIDC refresh token persisted: oidc-rt-556677`
10. `debug dump contained refresh_token=ghr_123456789`
11. `new refresh token for user42: ref-42-prod-9988`
12. `grant_type=refresh_token token=rt-client-111`
13. `offline_access refresh token issued: offline_rt_222`
14. `refresh token validation failed for rt_api_8733`
15. `security cache -> refreshToken svcrefresh778`
16. `auth callback payload includes refresh_token "refresh-dev-123"`
17. `persisted refresh token in session store: 1//0gExample`
18. `renewal request with refreshToken customer-rt-55`
19. `refresh_token leaked via exception context: abc.refresh.999`
20. `trace token set: refresh_token=corp-oidc-411`

## 5. Session-IDs

**Risikostufe:** hoch

**Beschreibung:** Session-IDs koennen Session Hijacking ermoeglichen, insbesondere wenn sie in Web- oder Anwendungsserver-Logs auftauchen. Das Risiko steigt, wenn keine zusaetzlichen Bindungen an IP, Device oder MFA bestehen.

**20 typische Findings:**

1. `JSESSIONID=8F3C1A9D7E4B22CC11AA0099DD44EE55`
2. `sessionId=7ab1e4c2-6dd4-4c53-9a6b-0b77f2d91c31`
3. `Set-Cookie: SESSION=4c9f9e1d0e2145f7a5aa3f7d2e8b9c11`
4. `invalidating session 1D8B4A22C991EE`
5. `HTTP session id leaked: SESS-2026-04-11-7788`
6. `user context session=abc123def456ghi789`
7. `session identifier SID9988776655`
8. `cookie value jsessionid=F0AABBCCDDEE112233`
9. `request correlated with sessionId prod-web-332211`
10. `session token found in URL: ;jsessionid=AA11BB22CC33`
11. `existing session ID 77f8c7b271e5400ab997`
12. `created session=mobile-session-4411`
13. `SSO session id=IDP-SESSION-991122`
14. `remembered session identifier rem-55667788`
15. `security audit: sessionId=tenant1-user73-abc`
16. `cookie dump: LTSESSIONID=9000aa11bb22`
17. `resumed session c6f4d91a847f4d6b`
18. `session key in request context: sess_1234_prod`
19. `corrupted session id=oldportal-009988`
20. `logout request for sessionId 6bfa32c0e98c`

## 6. JWTs

**Risikostufe:** hoch

**Beschreibung:** JSON Web Tokens enthalten oft Claims zu Identitaet, Rollen, Tenants oder Berechtigungen. Auch wenn sie signiert sind, koennen sie bei Leakage direkt wiederverwendet oder fuer Reconnaissance missbraucht werden.

**20 typische Findings:**

1. `jwt=eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIn0.sig001`
2. `id_token: eyJraWQiOiJrMSIsImFsZyI6IlJTMjU2In0.payload.sig`
3. `Authorization Bearer eyJhbGciOiJIUzI1NiJ9.payload.sig`
4. `received JWT for downstream call: eyJ0eXAiOiJKV1QifQ.claims.sign`
5. `parsed token header=eyJhbGciOiJSUzI1NiJ9`
6. `jwtToken=eyJzdWIiOiJqb2huIn0.payload.signature`
7. `SSO id_token cached: eyJhdWQiOiJwb3J0YWwifQ.abc.xyz`
8. `OpenID token dump: eyJpc3MiOiJodHRwczovL2lkcCJ9.claim.sig`
9. `JWT validation failed for token eyJraWQiOiIxMjMifQ.body.sig`
10. `security context jwt=eyJyb2xlcyI6WyJBRE1JTiJdfQ.pl.sig`
11. `forwarding signed jwt token ext.eyJ0ZW5hbnQiOiIxIn0.zz`
12. `oidc id_token leaked in trace`
13. `raw JWT claims token=eyJlbWFpbCI6Impkb2VAZXhhbXBsZS5kZSJ9.sig`
14. `downstream bearer jwt: eyJleHAiOjE3MDAwMDAwMDB9.a.b`
15. `session bootstrap JWT eyJub25jZSI6ImFiYyJ9.1.2`
16. `debug print token (jwt) = eyJzY29wZSI6InJlYWQifQ.3.4`
17. `stateless auth cookie contained JWT`
18. `jwt assertion=eyJzdWIiOiJzdmMtaW1wb3J0In0.sig.sig`
19. `token cache contains id_token eyJ0eXAiOiJKV1QifQ.55.66`
20. `request parameter jwt_token=eyJhbGciOiJFUzI1NiJ9.x.y`

## 7. OAuth-Client-Secrets

**Risikostufe:** sehr hoch

**Beschreibung:** Client-Secrets schuetzen vertrauliche OAuth- oder OpenID-Clients. Werden sie geloggt, koennen Angreifer sich als legitimer Client ausgeben und Token fuer geschuetzte Flows anfordern.

**20 typische Findings:**

1. `client_secret=oauthSecret9988`
2. `oauth.client.secret=prodClient#4455`
3. `token request body {"client_secret":"portal-secret-77"}`
4. `loaded clientSecret=openid-app-8899`
5. `secret for client web-frontend: webSecret2026`
6. `confidential client secret leaked: cc-sec-113355`
7. `clientSecret=8a7d6c5b4e3f2a1`
8. `oidc secret mismatch for client hr-portal`
9. `authorization server config client_secret svc-sync-44`
10. `OAuth secret stored in memory dump: oa-secret-7788`
11. `TRACE client_secret='api-bridge-secret'`
12. `Keycloak adapter secret=kc-client-9911`
13. `secret from env OAUTH_CLIENT_SECRET=adfs-prod-3322`
14. `client_credentials payload includes clientSecret m2m-abc-55`
15. `client secret rotation failed for oldSecret=legacy-oidc-7`
16. `Auth config: client-secret customerportal!oidc`
17. `saml bridge oauth secret bridge-secret-2026`
18. `debug config dump -> client_secret=finance-client-12`
19. `POST /token client_secret=partner-app-888`
20. `registered client secret value is secret-client-demo-1`

## 8. Datenbank-Zugangsdaten

**Risikostufe:** sehr hoch

**Beschreibung:** Datenbank-Zugangsdaten geben direkten Zugriff auf produktive Daten. Neben Benutzername und Passwort sind auch JDBC-URLs, DSNs und Connection-Strings mit eingebetteten Secrets kritisch.

**20 typische Findings:**

1. `jdbc:mysql://db01:3306/app?user=appuser&password=DbPass!22`
2. `db.username=finance_app`
3. `db.password=Finance#2026`
4. `datasource credentials appuser/Start#11`
5. `oracle.jdbc.password=OraSecret88`
6. `connection string Server=db01;User Id=sa;Password=SqlAdm!n22;`
7. `postgres://report:Rep0rt!23@db02:5432/reports`
8. `mongo uri mongodb://admin:Mongo#77@mongo1:27017/app`
9. `redis auth password=RedisSecret55`
10. `DB2 password found in config dump: db2prod88`
11. `user=svc_batch_db password=BatchDb#12`
12. `opening datasource with credential importer/Imp0rt!44`
13. `jdbc.user=customerportal`
14. `jdbc.password=PortalDb!1`
15. `database login failed for user etl_user with password Etl#5566`
16. `secret in Hikari config: password=PoolSecret!9`
17. `db credential rotation old password LegacyDB77`
18. `RDS endpoint with password parameter detected`
19. `database account app_readonly exposed in debug output`
20. `loaded connection properties: user=crm_app, password=Crm!2026`

## 9. SSH-Private-Keys

**Risikostufe:** sehr hoch

**Beschreibung:** SSH-Private-Keys koennen Server-, Git- oder Deployment-Zugaenge kompromittieren. Selbst Teilsegmente solcher Schluessel in Logs sind schwerwiegend und sollten sofort behandelt werden.

**20 typische Findings:**

1. `-----BEGIN OPENSSH PRIVATE KEY-----`
2. `-----BEGIN RSA PRIVATE KEY-----`
3. `-----BEGIN EC PRIVATE KEY-----`
4. `private_key=-----BEGIN OPENSSH PRIVATE KEY-----`
5. `deploy key fragment: b3BlbnNzaC1rZXktdjEAAAAABG5vbmU`
6. `ssh identity loaded from string: -----BEGIN RSA PRIVATE KEY-----`
7. `key material starts with MIIEpAIBAAKCAQEA`
8. `pem content leaked in debug log`
9. `SSH private key passphrase prompt for id_rsa_prod`
10. `parsed private key block length 1679`
11. `temporary file contained OPENSSH private key`
12. `Ansible log printed private key header`
13. `CI secret dump shows RSA PRIVATE KEY`
14. `ssh-keyscan step accidentally echoed private key`
15. `deployment credential includes privateKey value`
16. `vault export revealed ssh private key blob`
17. `decoded PEM begins with -----BEGIN`
18. `git deploy process read private key from env`
19. `private key footer found: -----END RSA PRIVATE KEY-----`
20. `k8s secret mounted key id_rsa content logged`

## 10. TLS- oder Zertifikats-Private-Keys

**Risikostufe:** sehr hoch

**Beschreibung:** Private Keys fuer TLS-Zertifikate erlauben das Ausgeben oder Mitlesen vertraulicher Verbindungen. Ein Leak gefaehrdet Authentizitaet, Vertraulichkeit und Vertrauen in die gesamte Kommunikationsstrecke.

**20 typische Findings:**

1. `-----BEGIN PRIVATE KEY-----`
2. `-----BEGIN ENCRYPTED PRIVATE KEY-----`
3. `tls.private.key=-----BEGIN PRIVATE KEY-----`
4. `certificate key alias server-key exported with private material`
5. `PKCS8 key content starts with MIIEvQIBADANBgkq`
6. `ssl key password=Keystore#8899`
7. `keystore entry contains private key for www.example.internal`
8. `openssl output printed unencrypted private key`
9. `PEM block leaked: -----BEGIN ENCRYPTED PRIVATE KEY-----`
10. `server.key content loaded into memory dump`
11. `debug trace includes x509 private key bytes`
12. `TLS bootstrap emitted private key path and contents`
13. `certificate import log contained private key blob`
14. `loaded PKCS12 with key password Changeit!77`
15. `kubernetes tls.key secret value logged`
16. `sslContext initialized with inline private key`
17. `footer found: -----END PRIVATE KEY-----`
18. `nginx key file /etc/ssl/private/site.key echoed in trace`
19. `private key rotation old key material still present in log`
20. `java keystore export exposed private key bytes`

## 11. Kreditkarteninformationen

**Risikostufe:** sehr hoch

**Beschreibung:** Kreditkartendaten unterliegen strengen regulatorischen Anforderungen und koennen direkt fuer Betrug missbraucht werden. Bereits PAN, Ablaufdatum oder CVV in Kombination sind hochkritisch.

**20 typische Findings:**

1. `cardNumber=4111111111111111`
2. `PAN 5500000000000004 approved`
3. `credit_card=340000000000009`
4. `payment payload {"card":"4000056655665556"}`
5. `masked incorrectly, full card 2223000048400011`
6. `cc=6011000000000004`
7. `visa number 4242424242424242 in request`
8. `mastercard=5555555555554444`
9. `amex=378282246310005`
10. `diners card 30569309025904 detected`
11. `Discover PAN 6011111111111117`
12. `stored card number 3530111333300000`
13. `payment tokenization input card=4000002500003155`
14. `authorization with account 5200828282828210`
15. `billing debug: pan 4111111111111234, exp 12/28`
16. `customer entered card number 4007000000027`
17. `recurring payment used card 5555555555555557`
18. `fallback capture printed full PAN 5105105105105100`
19. `card validation failed for 4012888888881881`
20. `cvv present with PAN 4111111111111111`

## 12. IBANs oder Bankkontodaten

**Risikostufe:** hoch

**Beschreibung:** Bankverbindungsdaten sind sensible Finanzdaten. Sie ermoeglichen Betrugsversuche, Social Engineering und die Zuordnung von Personen oder Unternehmen zu konkreten Konten.

**20 typische Findings:**

1. `iban=DE89370400440532013000`
2. `customer IBAN DE75512108001245126199`
3. `payment account FR7630006000011234567890189`
4. `SEPA debtor IBAN NL91ABNA0417164300`
5. `creditorAccount=GB29NWBK60161331926819`
6. `bankAccount=DE12500105170648489890`
7. `BIC/IBAN pair logged: COBADEFFXXX / DE44500105175407324931`
8. `transfer target IBAN ES9121000418450200051332`
9. `refund account IT60X0542811101000000123456`
10. `bank details: CH9300762011623852957`
11. `account holder provided IBAN AT611904300234573201`
12. `batch payment row contains BE68539007547034`
13. `incoming payload "iban":"PL61109010140000071219812874"`
14. `beneficiary account CZ6508000000192000145399`
15. `mandate data contains LU280019400644750000`
16. `export line leaked account DE02120300000000202051`
17. `credit transfer requested to NO9386011117947`
18. `banking API body iban=PT50000201231234567890154`
19. `supplier payout account IE29AIBK93115212345678`
20. `legacy konto string IBAN: DE68210501700012345678`

## 13. Sozialversicherungsnummern oder Steuer-IDs

**Risikostufe:** hoch

**Beschreibung:** Diese Identifikatoren sind langlebig und personenbezogen. Sie eignen sich fuer Identitaetsmissbrauch, Betrug und die Verknuepfung von Datensaetzen ueber Systeme hinweg.

**20 typische Findings:**

1. `steuerId=52481530987`
2. `taxId=12-345-6789`
3. `ssn=123-45-6789`
4. `socialSecurityNumber=987-65-4321`
5. `deutsche Rentenversicherungsnummer 65 170839 J 008`
6. `svnr=12 120863 M 045`
7. `TIN 52481530987 validated`
8. `employee tax-id 43852976104`
9. `person record contains SSN 321-54-9876`
10. `payload {"steuer_id":"65432178901"}`
11. `insurance number 39 170839 K 08 8`
12. `social security no. 555-77-8888`
13. `tax identifier stored: 47012938475`
14. `gov id field taxId=71122334455`
15. `debug: sv-nummer 23 110470 W 091`
16. `wage import row with ssn 456-78-9012`
17. `eTIN output 102-34-5678`
18. `citizen tax number 61394827560`
19. `sync failed for employee with insuranceNo 81 220560 R 122`
20. `json body includes social_security_number 234-56-7890`

## 14. Personalausweis- oder Reisepassnummern

**Risikostufe:** hoch

**Beschreibung:** Ausweis- und Passnummern sind starke Identifikatoren fuer Personen. In Verbindung mit weiteren Stammdaten koennen sie fuer Identitaetsbetrug oder unzulaessige Profilbildung genutzt werden.

**20 typische Findings:**

1. `passportNumber=C01X00T47`
2. `reisepass=CF4T7P2L9`
3. `idCardNumber=L01X12345`
4. `personalausweis=T220001293`
5. `mrz doc number C4L8X22Y1`
6. `travelDocumentNumber=98AA77351`
7. `passport_no=PA55DE123`
8. `nationalIdDocument=IDD228877`
9. `customer identity doc C11T09Q77 verified`
10. `id card number logged: X2K9P55R1`
11. `visa application passport=71MNC9982`
12. `ident payload {"passport":"P0L9X8C77"}`
13. `documentNumber=AA8837462`
14. `proofOfIdentity number B7X220094`
15. `scan result passport no. L33920184`
16. `ID document check for T220001293 succeeded`
17. `eID reference docNumber C09Z77112`
18. `support ticket includes reisepassnummer A12B99871`
19. `manual verification entered idCard=Z77100441`
20. `KYC request body documentNo=R88T12003`

## 15. E-Mail-Adressen

**Risikostufe:** mittel

**Beschreibung:** Einzelne E-Mail-Adressen sind oft weniger kritisch als Secrets, aber sie sind personenbezogene Daten und in hoher Menge oder mit Kontextbezug ein relevantes Datenschutzrisiko.

**20 typische Findings:**

1. `user.email=anna.mueller@example.de`
2. `contactMail=max.meier@firma-intern.de`
3. `Sending mail to service.team@example.org`
4. `reset requested for julia.schmidt@test.de`
5. `customerEmail=thomas.weber@beispiel.com`
6. `fromAddress=noreply@portal.example`
7. `replyTo=vertrieb@beispielfirma.de`
8. `mail recipient sabine.klein@kunde.eu`
9. `invalid email john.doe@example.net`
10. `notification target qa-team@example.io`
11. `payload {"email":"lena.fischer@example.de"}`
12. `username mapped to peter.hoffmann@corp.local`
13. `cc list contains maria.bauer@example.de`
14. `support requestor emil.wagner@service.test`
15. `mailAddress=lea.koch@customer.example`
16. `subscriber timo.lang@example.de unsubscribed`
17. `bounce for oliver.neumann@mail.example`
18. `directory sync includes nina.wolf@example.de`
19. `customer account mapped to felix.richter@example.de`
20. `login name equals eva.hartmann@example.de`

## 16. Telefonnummern

**Risikostufe:** mittel

**Beschreibung:** Telefonnummern sind personenbezogene Kontaktinformationen. In Support-, CRM- oder Gesundheitskontexten koennen sie Betroffene direkt identifizieren und fuer Missbrauch genutzt werden.

**20 typische Findings:**

1. `phone=+49 171 1234567`
2. `telephone=030 12345678`
3. `mobile=0151-23456789`
4. `customerPhone=+41 44 668 18 00`
5. `contact number +43 660 1234567`
6. `tel:+49-89-1234-5678`
7. `payload {"phone":"0176 99887766"}`
8. `msisdn=491701112233`
9. `callback number 0221/998877`
10. `emergencyContact=+49 30 76543210`
11. `hotline caller 0049 151 55556666`
12. `landline=040-33445566`
13. `support user phone 089 445566`
14. `dialed number +352 621 123456`
15. `fax/phone field 069 2002 100`
16. `contactMobile=+49 (171) 7654321`
17. `crm import row contains 0160 22334455`
18. `voip target +1 202 555 0178`
19. `private phone 0711 889900`
20. `notification sent to +49 1522 3344556`

## 17. Vollstaendige Postanschriften

**Risikostufe:** mittel

**Beschreibung:** Vollstaendige Anschriften identifizieren Personen oder Unternehmen oft eindeutig. Sie sind besonders sensibel, wenn sie mit Namen, Vertragsdaten oder Gesundheitsinformationen kombiniert werden.

**20 typische Findings:**

1. `address=Hauptstrasse 12, 10115 Berlin`
2. `shippingAddress=Bahnhofstrasse 8, 80331 Muenchen`
3. `customer address: Marktgasse 4, 4051 Basel`
4. `invoice_to=Koenigstrasse 22, 70173 Stuttgart`
5. `payload {"street":"Gartenweg 7","zip":"50667","city":"Koeln"}`
6. `delivery target Lindenallee 55, 04109 Leipzig`
7. `residence Adlerweg 3, 40210 Duesseldorf`
8. `user home address Bahnhofplatz 1, 8001 Zuerich`
9. `postal contact Mozartstrasse 14, 81675 Muenchen`
10. `patient address Rosenstrasse 19, 20095 Hamburg`
11. `office moved to Schillerstrasse 31, 60313 Frankfurt`
12. `billing address Seestrasse 9, 78462 Konstanz`
13. `support note includes Birkenweg 27, 24103 Kiel`
14. `crm export with Dorfstrasse 2, 01067 Dresden`
15. `recipient address Poststrasse 44, 53111 Bonn`
16. `logistics route to Bahnhofring 6, 28195 Bremen`
17. `address line Am Markt 11, 14467 Potsdam`
18. `customer master data: Schulweg 13, 66111 Saarbruecken`
19. `contact record contains Tulpenweg 5, 18055 Rostock`
20. `shipping label preview Karlstrasse 88, 76133 Karlsruhe`

## 18. Geburtsdaten

**Risikostufe:** mittel

**Beschreibung:** Geburtsdaten sind klassische Stammdaten mit hoher Re-Identifikationskraft. Zusammen mit Namen oder Adressen koennen sie Personen sehr praezise identifizieren.

**20 typische Findings:**

1. `dateOfBirth=1988-04-17`
2. `geburtsdatum=17.04.1988`
3. `dob=1979-11-02`
4. `customer birthDate 2001-06-30`
5. `payload {"dob":"1994-12-09"}`
6. `patient born on 03.08.1975`
7. `KYC field birth_date=1985/02/14`
8. `member birthday 1968-09-21`
9. `user profile includes 12.01.1990 as birth date`
10. `birthDate=2007-01-04`
11. `crm import row DOB 31.05.1982`
12. `geb. am 24.10.1971`
13. `subscriber date of birth 1999-07-11`
14. `eligibility check for birthday 1957-03-01`
15. `record contains geburtsdatum 08.08.1988`
16. `insuredPersonDob=1973-12-27`
17. `metadata birthdate: 1992-05-05`
18. `passport application DOB 14.02.2000`
19. `debug profile -> born 1980-01-19`
20. `user input field birth_date=1996-09-16`

## 19. Gesundheitsdaten oder Diagnosen

**Risikostufe:** sehr hoch

**Beschreibung:** Gesundheitsdaten gehoeren zu den besonders schuetzenswerten personenbezogenen Daten. Diagnosen, Behandlungen oder Medikationshinweise in Logs koennen gravierende Datenschutz- und Compliance-Verstoesse ausloesen.

**20 typische Findings:**

1. `diagnosis=Diabetes mellitus Typ 2`
2. `ICD10=E11.9`
3. `patient has hypertension and obesity`
4. `medication=Metformin 500mg`
5. `lab result HIV negative`
6. `diagnosis code C50.9 documented`
7. `therapy plan includes Psychotherapie`
8. `payload {"diagnosis":"Asthma bronchiale"}`
9. `allergy note: Penicillin`
10. `patient history contains depression episode`
11. `medical finding: fracture of left radius`
12. `ICD10=F32.1`
13. `treatment=Chemotherapie Zyklus 3`
14. `blood glucose value linked to patient record`
15. `triage note mentions Schwangerschaft`
16. `health status field COPD GOLD II`
17. `lab import row Hepatitis B positive`
18. `ePA export contains diagnosis Migraene`
19. `medical certificate reason Burnout`
20. `clinical note: post-operative infection`

## 20. Interne Systeminformationen mit Sicherheitsbezug

**Risikostufe:** hoch

**Beschreibung:** Sicherheitsrelevante Systemdetails erleichtern Reconnaissance und nachgelagerte Angriffe. Dazu gehoeren interne Hostnamen, Admin-URLs, Architekturdetails, Firewall-Regeln, Usernamen oder ungepatchte Versionsstaende mit Sicherheitsbezug.

**20 typische Findings:**

1. `admin console available at https://admin-intern-01:9443/ibm/console`
2. `internal host db-prod-02.corp.local reachable`
3. `firewall rule opened from 10.10.4.0/24 to 10.20.8.15:5432`
4. `SSH access enabled for bastion-prod-1`
5. `service running with root privileges`
6. `Tomcat 9.0.65 detected on internal node`
7. `outdated OpenSSL 1.0.2u in use`
8. `debug endpoint /actuator/env exposed internally`
9. `stack trace references /opt/apps/payment-service/config-prod.yml`
10. `loaded keystore from /srv/keys/prod-keystore.p12`
11. `LDAP bind user cn=svc_sync,ou=system,dc=corp,dc=local`
12. `security group sg-0ab123cd456ef789 allows 0.0.0.0/0 on 22`
13. `internal API base URL http://auth-backend.internal:8080`
14. `VPN profile name CorpAdmin-FullAccess`
15. `privileged account svc-deploy-admin used for rollout`
16. `backup location smb://backup-intern/prod-secrets`
17. `exception contains full path /etc/nginx/conf.d/admin.conf`
18. `kubernetes namespace prod-sec-tools listed in trace`
19. `feature flag disables CSRF check for admin path`
20. `reverse proxy trusts x-forwarded-for from any source`

## Hinweise zur Nutzung

- Die Beispiele koennen als Testdaten fuer Erkennungsmuster, Dokumentation oder Demo-Logs verwendet werden.
- Fuer produktive Testfaelle sollten die Werte bei Bedarf anonymisiert, maskiert oder in synthetische Daten ueberfuehrt werden.
- Mehrere der Beispiele sind absichtlich nahe an realen Formaten gehalten, damit Suchmuster, Regulare Ausdruecke und Feld-Erkennung belastbar getestet werden koennen.
