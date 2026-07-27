from __future__ import annotations

SUPPORTED_PRIVACY_LANGUAGES = ("en", "ru", "fr", "de", "es", "sr")

PRIVACY_COPY = {'en': {'title': 'Privacy policy',
        'notice': 'Effective 24 July 2026. This policy describes the current free stage of the service.',
        'h_controller': 'Who processes data',
        'p_controller': 'ChinaTradeResolve is an independent commercial-dispute support project. The responsible '
                        'operator and contact details are shown below.',
        'h_data': 'Data collected',
        'p_data': 'The application collects name, email, country, language, order details and a short dispute '
                  'description. It may also store campaign tags (such as UTM source and campaign), the first page '
                  'visited and, when available, only the origin of the referring website. The private case page may '
                  'store up to 20 key PDF or image files and the resulting evidence-analysis report. Payment-card '
                  'data is not collected.',
        'h_purpose': 'How data is used',
        'p_purpose': 'Data is used to register and screen applications, communicate with applicants, review cases, '
                     'understand which public information or promotion channels bring useful enquiries, protect the '
                     'service from abuse and meet mandatory legal requirements.',
        'h_ai': 'AI processing',
        'p_ai': 'With separate voluntary consent, AI may organise uploaded documents. The public assistant may also '
                'transcribe a voice recording: audio is sent only for transcription, is not stored in the case '
                'database and is removed from server memory immediately after processing. The editable transcript is '
                'sent to the assistant only if the user presses Send. Provider abuse-monitoring logs may follow its '
                'retention rules. Important conclusions require human verification.',
        'h_share': 'Data recipients',
        'p_share': 'Access may be provided only to infrastructure, email and configured AI providers as necessary to '
                   'operate the service. Uploaded files are sent to the configured AI provider only when AI analysis '
                   'is requested and consented to. Data is not sold and is not sent to a supplier or marketplace '
                   'without your decision.',
        'h_store': 'Retention and deletion',
        'p_store': 'Closed cases are anonymised after {retention_days} days and any inactive case after '
                   '{inactive_retention_days} days. The private status link allows immediate deletion of the case '
                   'and its files.',
        'h_rights': 'Your rights',
        'p_rights': 'The private status link lets you withdraw consent for future AI processing and delete the '
                    'stored AI report, or permanently delete the whole case. Contact us for access or correction '
                    'requests.',
        'h_security': 'Security',
        'p_security': 'Do not upload passwords, seed phrases, private keys, full card numbers or unnecessary '
                      'identity documents. Images are re-encoded to remove embedded metadata. Internet transmission '
                      'cannot be guaranteed to be completely secure.',
        'back': 'Return to website',
        'development_notice': 'This local preview is not accepting public applications. Operator details must be '
                              'configured before public launch.',
        'meta_description': 'How ChinaTradeResolve collects, uses, protects and deletes application, case, document '
                            'and campaign-source data.',
        'language_label': 'Language'},
 'fr': {'title': 'Politique de confidentialité',
        'notice': 'En vigueur depuis le 24 juillet 2026. Cette politique décrit la phase gratuite actuelle du '
                  'service.',
        'h_controller': 'Qui traite les données',
        'p_controller': 'ChinaTradeResolve est un projet indépendant d’assistance commerciale aux litiges. Les '
                        'coordonnées de l’opérateur responsable figurent ci-dessous.',
        'h_data': 'Données collectées',
        'p_data': 'La demande recueille le nom, l’adresse e-mail, le pays, la langue, les données de commande et une '
                  'brève description. Elle peut aussi conserver les paramètres de campagne (par exemple la source '
                  'UTM et le nom de campagne), la première page visitée et, lorsqu’elle est disponible, uniquement '
                  'l’origine du site référent. La page privée peut conserver jusqu’à 20 PDF ou images clés et le '
                  'rapport d’analyse. Aucune donnée de carte bancaire n’est collectée. Si la balise facultative Yandex Metrica est activée, elle peut également traiter des données techniques de visite et de navigation à des fins statistiques.',
        'h_purpose': 'Utilisation des données',
        'p_purpose': 'Les données servent à enregistrer et examiner les demandes, communiquer avec les demandeurs, '
                     'analyser les dossiers, comprendre quelles publications ou sources de promotion apportent des '
                     'demandes utiles, protéger le service contre les abus et respecter les obligations légales.',
        'h_ai': 'Traitement par l’IA',
        'p_ai': 'Avec un consentement volontaire distinct, l’IA peut organiser les documents téléversés. L’assistant '
                'public peut aussi transcrire un enregistrement vocal : l’audio est envoyé uniquement pour '
                'transcription, n’est pas conservé dans la base des dossiers et est supprimé de la mémoire du '
                'serveur après traitement. Le texte n’est envoyé à l’assistant que si l’utilisateur appuie sur '
                'Envoyer. Les journaux du fournisseur suivent ses règles de conservation. Toute conclusion '
                'importante est vérifiée par une personne.',
        'h_share': 'Destinataires des données',
        'p_share': 'L’accès est limité aux prestataires d’infrastructure, de messagerie et d’IA nécessaires. Les '
                   'fichiers ne sont transmis au prestataire d’IA configuré que lorsqu’une analyse est demandée avec '
                   'consentement. Les données ne sont pas vendues ni envoyées au fournisseur ou à la plateforme sans '
                   'votre décision.',
        'h_store': 'Conservation et suppression',
        'p_store': 'Les dossiers clos sont anonymisés après {retention_days} jours et tout dossier inactif après '
                   '{inactive_retention_days} jours. Le lien privé de suivi permet de supprimer immédiatement le '
                   'dossier et ses fichiers.',
        'h_rights': 'Vos droits',
        'p_rights': 'Le lien privé permet de retirer le consentement à l’IA et de supprimer le rapport IA, ou de '
                    'supprimer définitivement tout le dossier. Contactez-nous pour l’accès ou la rectification.',
        'h_security': 'Sécurité',
        'p_security': 'Ne téléversez pas de mots de passe, phrases de récupération, clés privées, numéros complets '
                      'de carte ou pièces d’identité inutiles. Les images sont réencodées pour supprimer les '
                      'métadonnées. Une transmission totalement sûre ne peut être garantie.',
        'back': 'Retour au site',
        'development_notice': 'Cet aperçu local n’accepte pas de demandes publiques. Les informations de l’opérateur '
                              'doivent être configurées avant le lancement.',
        'meta_description': 'Comment ChinaTradeResolve collecte, utilise, protège et supprime les données de '
                            'demande, de dossier, de documents et de provenance.',
        'language_label': 'Langue'},
 'de': {'title': 'Datenschutzerklärung',
        'notice': 'Gültig ab 24. Juli 2026. Diese Erklärung beschreibt die aktuelle kostenlose Phase des Dienstes.',
        'h_controller': 'Wer Daten verarbeitet',
        'p_controller': 'ChinaTradeResolve ist ein unabhängiges Projekt zur kaufmännischen Unterstützung bei '
                        'Streitfällen. Angaben zum verantwortlichen Betreiber und Kontakt stehen unten.',
        'h_data': 'Erhobene Daten',
        'p_data': 'Bei der Antragstellung werden Name, E-Mail, Land, Sprache, Bestelldaten und eine kurze '
                  'Beschreibung erhoben. Zusätzlich können Kampagnenangaben (zum Beispiel UTM-Quelle und '
                  'Kampagnenname), die zuerst besuchte Seite und – soweit vorhanden – nur der Ursprung der '
                  'verweisenden Website gespeichert werden. Auf der privaten Fallseite können bis zu 20 wichtige '
                  'PDF- oder Bilddateien und der Analysebericht gespeichert werden. Zahlungskartendaten werden nicht '
                  'erhoben.',
        'h_purpose': 'Verwendung der Daten',
        'p_purpose': 'Die Daten werden zur Registrierung und Vorprüfung von Anträgen, zur Kommunikation, '
                     'Fallprüfung, Auswertung hilfreicher Veröffentlichungs- und Werbequellen, zum Schutz vor '
                     'Missbrauch und zur Erfüllung zwingender rechtlicher Pflichten verwendet.',
        'h_ai': 'KI-Verarbeitung',
        'p_ai': 'Mit gesonderter freiwilliger Einwilligung kann KI hochgeladene Dokumente ordnen. Der öffentliche '
                'Assistent kann auch eine Sprachaufnahme transkribieren: Audio wird nur zur Transkription gesendet, '
                'nicht in der Falldatenbank gespeichert und direkt nach der Verarbeitung aus dem Serverspeicher '
                'entfernt. Der Text wird erst nach dem Drücken von Senden an den Assistenten übermittelt. '
                'Anbieterprotokolle unterliegen dessen Aufbewahrungsregeln. Wichtige Schlussfolgerungen werden '
                'menschlich geprüft.',
        'h_share': 'Empfänger der Daten',
        'p_share': 'Zugriff erhalten nur notwendige Infrastruktur-, E-Mail- und KI-Anbieter. Dateien werden nur bei '
                   'angeforderter und eingewilligter KI-Analyse an den konfigurierten KI-Anbieter übermittelt. Daten '
                   'werden nicht verkauft und ohne Ihre Entscheidung nicht an Lieferanten oder Marktplätze gesendet.',
        'h_store': 'Speicherung und Löschung',
        'p_store': 'Geschlossene Fälle werden nach {retention_days} Tagen anonymisiert, inaktive Fälle nach '
                   '{inactive_retention_days} Tagen. Über den privaten Statuslink können der Fall und seine Dateien '
                   'sofort gelöscht werden.',
        'h_rights': 'Ihre Rechte',
        'p_rights': 'Über den privaten Statuslink können Sie die KI-Einwilligung widerrufen und den KI-Bericht '
                    'löschen oder den gesamten Fall endgültig löschen. Kontaktieren Sie uns für Auskunft oder '
                    'Berichtigung.',
        'h_security': 'Sicherheit',
        'p_security': 'Laden Sie keine Passwörter, Seed-Phrasen, privaten Schlüssel, vollständigen Kartennummern '
                      'oder unnötigen Ausweisdokumente hoch. Bilder werden zur Entfernung von Metadaten neu kodiert. '
                      'Eine vollständig sichere Übertragung kann nicht garantiert werden.',
        'back': 'Zur Website zurückkehren',
        'development_notice': 'Diese lokale Vorschau nimmt keine öffentlichen Anträge an. Die Betreiberangaben '
                              'müssen vor dem öffentlichen Start konfiguriert werden.',
        'meta_description': 'Wie ChinaTradeResolve Antrags-, Fall-, Dokument- und Herkunftsdaten erhebt, verwendet, '
                            'schützt und löscht.',
        'language_label': 'Sprache'},
 'es': {'title': 'Política de privacidad',
        'notice': 'Vigente desde el 24 de julio de 2026. Esta política describe la fase gratuita actual del '
                  'servicio.',
        'h_controller': 'Quién trata los datos',
        'p_controller': 'ChinaTradeResolve es un proyecto independiente de apoyo comercial en disputas. Los datos '
                        'del operador responsable y de contacto aparecen a continuación.',
        'h_data': 'Datos recopilados',
        'p_data': 'La solicitud recopila nombre, correo electrónico, país, idioma, datos del pedido y una breve '
                  'descripción. También puede guardar etiquetas de campaña (por ejemplo, fuente UTM y nombre de '
                  'campaña), la primera página visitada y, cuando esté disponible, solo el origen del sitio '
                  'remitente. La página privada puede almacenar hasta 20 PDF o imágenes clave y el informe de '
                  'análisis. No se recopilan datos de tarjetas de pago. Si se activa la etiqueta opcional de Yandex Metrica, también puede tratar datos técnicos de visita y navegación para estadísticas del sitio.',
        'h_purpose': 'Uso de los datos',
        'p_purpose': 'Los datos se utilizan para registrar y revisar solicitudes, comunicarse con los solicitantes, '
                     'analizar casos, entender qué publicaciones o canales de promoción generan consultas útiles, '
                     'proteger el servicio contra abusos y cumplir obligaciones legales.',
        'h_ai': 'Tratamiento con IA',
        'p_ai': 'Con un consentimiento voluntario separado, la IA puede organizar los documentos subidos. El '
                'asistente público también puede transcribir una grabación de voz: el audio se envía solo para '
                'transcribirlo, no se guarda en la base de casos y se elimina de la memoria del servidor después del '
                'proceso. El texto se envía al asistente solo cuando el usuario pulsa Enviar. Los registros del '
                'proveedor siguen sus reglas de conservación. Las conclusiones importantes requieren revisión '
                'humana.',
        'h_share': 'Destinatarios de los datos',
        'p_share': 'El acceso se limita a los proveedores necesarios de infraestructura, correo e IA. Los archivos '
                   'solo se envían al proveedor de IA configurado cuando se solicita el análisis con consentimiento. '
                   'Los datos no se venden ni se envían al proveedor o plataforma sin su decisión.',
        'h_store': 'Conservación y eliminación',
        'p_store': 'Los casos cerrados se anonimizan después de {retention_days} días y los casos inactivos después '
                   'de {inactive_retention_days} días. El enlace privado de estado permite eliminar inmediatamente '
                   'el caso y sus archivos.',
        'h_rights': 'Sus derechos',
        'p_rights': 'El enlace privado permite retirar el consentimiento de IA y borrar el informe de IA, o eliminar '
                    'permanentemente todo el caso. Contáctenos para solicitar acceso o rectificación.',
        'h_security': 'Seguridad',
        'p_security': 'No cargue contraseñas, frases semilla, claves privadas, números completos de tarjeta ni '
                      'documentos de identidad innecesarios. Las imágenes se recodifican para eliminar metadatos. No '
                      'puede garantizarse una transmisión totalmente segura.',
        'back': 'Volver al sitio web',
        'development_notice': 'Esta vista previa local no acepta solicitudes públicas. Los datos del operador deben '
                              'configurarse antes del lanzamiento.',
        'meta_description': 'Cómo ChinaTradeResolve recopila, utiliza, protege y elimina datos de solicitudes, '
                            'casos, documentos y procedencia.',
        'language_label': 'Idioma'},
 'ru': {'title': 'Политика конфиденциальности',
        'notice': 'Действует с 24 июля 2026 года. Политика описывает текущий бесплатный этап сервиса.',
        'h_controller': 'Кто обрабатывает данные',
        'p_controller': 'ChinaTradeResolve — независимый проект коммерческой помощи в спорах. Данные ответственного '
                        'оператора и контакты указаны ниже.',
        'h_data': 'Какие данные собираются',
        'p_data': 'На этапе заявки собираются имя, электронная почта, страна, язык, сведения о заказе и краткое '
                  'описание спора. Также могут сохраняться метки рекламной кампании (например, UTM-источник и '
                  'название кампании), первая открытая страница и, при наличии, только адрес сайта-источника без '
                  'полного пути. На закрытой странице дела могут храниться до 20 ключевых PDF или изображений и '
                  'результат анализа доказательств. Платёжные данные банковских карт не собираются. Если включён необязательный счётчик Яндекс Метрики, он также может обрабатывать технические данные о посещении и навигации для статистики сайта.',
        'h_purpose': 'Зачем используются данные',
        'p_purpose': 'Данные используются для регистрации и предварительной проверки заявок, связи с заявителем, '
                     'рассмотрения дела, понимания того, какие публикации и каналы приводят полезные обращения, '
                     'защиты сервиса от злоупотреблений и выполнения обязательных требований закона.',
        'h_ai': 'Использование ИИ',
        'p_ai': 'При отдельном добровольном согласии ИИ может систематизировать загруженные документы. Публичный '
                'помощник также может расшифровать голосовую запись: аудио передаётся только для расшифровки, не '
                'сохраняется в базе дел и удаляется из памяти сервера сразу после обработки. Редактируемый текст '
                'передаётся помощнику только после нажатия «Отправить». Журналы провайдера могут храниться по его '
                'правилам. Важные выводы проверяет человек.',
        'h_share': 'Кому могут передаваться данные',
        'p_share': 'Доступ может предоставляться только поставщикам инфраструктуры, электронной почты и настроенного '
                   'ИИ-сервиса в объёме, необходимом для работы. Загруженные файлы передаются настроенному '
                   'ИИ-провайдеру только при запрошенном анализе и наличии согласия. Данные не продаются и не '
                   'передаются поставщику или площадке без вашего решения.',
        'h_store': 'Хранение и удаление',
        'p_store': 'Закрытые дела обезличиваются через {retention_days} дней, а любые неактивные дела — через '
                   '{inactive_retention_days} дней. По секретной ссылке статуса можно немедленно удалить дело и его '
                   'файлы.',
        'h_rights': 'Ваши права',
        'p_rights': 'По секретной ссылке можно отозвать согласие на будущую ИИ-обработку и удалить ИИ-отчёт либо '
                    'безвозвратно удалить всё дело. Для доступа или исправления данных свяжитесь с нами.',
        'h_security': 'Безопасность',
        'p_security': 'Не загружайте пароли, seed-фразы, приватные ключи, полные номера карт и ненужные документы '
                      'личности. Изображения перекодируются для удаления встроенных метаданных. Полностью безопасную '
                      'передачу через интернет гарантировать невозможно.',
        'back': 'Вернуться на сайт',
        'development_notice': 'Это локальная предварительная версия, которая не принимает публичные заявки. Данные '
                              'оператора необходимо настроить до запуска.',
        'meta_description': 'Как ChinaTradeResolve собирает, использует, защищает и удаляет данные заявок, дел, '
                            'документов и источников перехода.',
        'language_label': 'Язык'},
 'sr': {'title': 'Politika privatnosti',
        'notice': 'Važi od 24. jula 2026. Ova politika opisuje trenutnu besplatnu fazu usluge.',
        'h_controller': 'Ko obrađuje podatke',
        'p_controller': 'ChinaTradeResolve je nezavisan projekat komercijalne pomoći u sporovima. Podaci odgovornog '
                        'operatera i kontakt nalaze se ispod.',
        'h_data': 'Podaci koji se prikupljaju',
        'p_data': 'Prijava prikuplja ime, email, zemlju, jezik, podatke o porudžbini i kratak opis spora. Mogu se '
                  'sačuvati i oznake kampanje (na primer UTM izvor i naziv kampanje), prva posećena stranica i, kada '
                  'postoji, samo poreklo prethodnog sajta. Privatna stranica slučaja može čuvati do 20 ključnih PDF '
                  'ili slikovnih fajlova i izveštaj analize. Podaci platnih kartica se ne prikupljaju. Ako je uključen opcioni Yandex Metrica brojač, on takođe može obrađivati tehničke podatke o poseti i navigaciji radi statistike sajta.',
        'h_purpose': 'Kako se podaci koriste',
        'p_purpose': 'Podaci se koriste za registraciju i preliminarni pregled prijava, komunikaciju, pregled '
                     'slučaja, razumevanje koje objave i promotivni izvori donose korisne upite, zaštitu servisa od '
                     'zloupotrebe i ispunjavanje obaveznih zakonskih zahteva.',
        'h_ai': 'AI obrada',
        'p_ai': 'Uz posebnu dobrovoljnu saglasnost, AI može organizovati otpremljene dokumente. Javni pomoćnik može '
                'i da transkribuje glasovni snimak: audio se šalje samo radi transkripcije, ne čuva se u bazi '
                'slučajeva i uklanja se iz memorije servera odmah nakon obrade. Tekst se šalje pomoćniku tek kada '
                'korisnik pritisne Pošalji. Evidencije provajdera mogu pratiti njegova pravila čuvanja. Važne '
                'zaključke proverava čovek.',
        'h_share': 'Primaoci podataka',
        'p_share': 'Pristup je ograničen na neophodne infrastrukturne, email i AI pružaoce. Fajlovi se šalju '
                   'konfigurisanom AI pružaocu samo kada je analiza zatražena uz saglasnost. Podaci se ne prodaju i '
                   'ne šalju dobavljaču ili platformi bez vaše odluke.',
        'h_store': 'Čuvanje i brisanje',
        'p_store': 'Zatvoreni slučajevi se anonimizuju posle {retention_days} dana, a neaktivni slučajevi posle '
                   '{inactive_retention_days} dana. Privatni statusni link omogućava trenutno brisanje slučaja i '
                   'njegovih fajlova.',
        'h_rights': 'Vaša prava',
        'p_rights': 'Privatni statusni link omogućava povlačenje AI saglasnosti i brisanje AI izveštaja ili trajno '
                    'brisanje celog slučaja. Kontaktirajte nas radi pristupa ili ispravke.',
        'h_security': 'Bezbednost',
        'p_security': 'Ne otpremajte lozinke, seed fraze, privatne ključeve, pune brojeve kartica ili nepotrebna '
                      'lična dokumenta. Slike se ponovo kodiraju radi uklanjanja metapodataka. Potpuno bezbedan '
                      'prenos preko interneta se ne može garantovati.',
        'back': 'Povratak na sajt',
        'development_notice': 'Ovo je lokalni pregled koji ne prima javne prijave. Podaci operatera moraju biti '
                              'podešeni pre javnog pokretanja.',
        'meta_description': 'Kako ChinaTradeResolve prikuplja, koristi, štiti i briše podatke prijava, slučajeva, '
                            'dokumenata i izvora posete.',
        'language_label': 'Jezik'}}

_METRIKA_PRIVACY_DISCLOSURE = {
    "en": "If the optional Yandex Metrica counter is enabled, it may also process technical visit and navigation data for site statistics.",
    "ru": "Если включён необязательный счётчик Яндекс Метрики, он также может обрабатывать технические данные о посещении и навигации для статистики сайта.",
    "fr": "Si la balise facultative Yandex Metrica est activée, elle peut également traiter des données techniques de visite et de navigation à des fins statistiques.",
    "de": "Wenn der optionale Zähler Yandex Metrica aktiviert ist, kann er außerdem technische Besuchs- und Navigationsdaten für die Website-Statistik verarbeiten.",
    "es": "Si se activa el contador opcional de Yandex Metrica, también puede tratar datos técnicos de visita y navegación para las estadísticas del sitio.",
    "sr": "Ako je uključen opcioni Yandex Metrica brojač, on takođe može obrađivati tehničke podatke o poseti i navigaciji radi statistike sajta.",
}

for _language, _sentence in _METRIKA_PRIVACY_DISCLOSURE.items():
    if _sentence not in PRIVACY_COPY[_language]["p_data"]:
        PRIVACY_COPY[_language]["p_data"] += " " + _sentence

