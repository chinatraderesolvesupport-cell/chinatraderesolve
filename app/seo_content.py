from __future__ import annotations

SUPPORTED_LANGUAGES = ("en", "ru", "fr", "de", "es", "sr")

HOME_SEO = {
    "en": {
        "title": "ChinaTradeResolve — help with disputes involving Chinese suppliers",
        "description": "Organize evidence, identify missing documents and receive a preliminary assessment for an Alibaba or Chinese-supplier dispute.",
        "og_description": "Independent preliminary review of supplier disputes, evidence and next steps.",
    },
    "ru": {
        "title": "ChinaTradeResolve — разбор споров с китайскими поставщиками",
        "description": "Опишите спор с китайским поставщиком и получите предварительную оценку позиции, недостающих доказательств и следующих действий.",
        "og_description": "Предварительная оценка позиции, доказательств и следующих действий без завышенных обещаний.",
    },
    "fr": {
        "title": "ChinaTradeResolve — aide pour les litiges avec des fournisseurs chinois",
        "description": "Organisez les preuves, repérez les documents manquants et obtenez une évaluation préliminaire de votre litige fournisseur.",
        "og_description": "Évaluation indépendante et préliminaire des preuves et prochaines étapes.",
    },
    "de": {
        "title": "ChinaTradeResolve — Hilfe bei Streitfällen mit chinesischen Lieferanten",
        "description": "Beweise ordnen, fehlende Unterlagen erkennen und eine vorläufige Einschätzung zu Ihrem Lieferantenstreit erhalten.",
        "og_description": "Unabhängige vorläufige Prüfung von Beweisen und nächsten Schritten.",
    },
    "es": {
        "title": "ChinaTradeResolve — ayuda en disputas con proveedores chinos",
        "description": "Organice pruebas, detecte documentos faltantes y obtenga una evaluación preliminar de su disputa con un proveedor.",
        "og_description": "Revisión preliminar e independiente de pruebas y próximos pasos.",
    },
    "sr": {
        "title": "ChinaTradeResolve — pomoć u sporovima sa kineskim dobavljačima",
        "description": "Organizujte dokaze, utvrdite šta nedostaje i dobijte preliminarnu procenu spora sa dobavljačem.",
        "og_description": "Nezavisna preliminarna procena dokaza i narednih koraka.",
    },
}

GUIDE_HUB_COPY = {
    "en": {"title": "Practical guides for supplier disputes", "intro": "Clear checklists for buyers dealing with non-delivery, quality problems, wrong specifications or an Alibaba refund dispute.", "read": "Read guide", "home": "Back to ChinaTradeResolve", "note": "Educational information only; platform rules and deadlines can change."},
    "ru": {"title": "Практические руководства по спорам с поставщиками", "intro": "Понятные памятки для случаев непоставки, брака, несоответствия спецификации и споров о возврате на Alibaba.", "read": "Открыть руководство", "home": "Вернуться на ChinaTradeResolve", "note": "Материалы носят информационный характер; правила площадок и сроки могут меняться."},
    "fr": {"title": "Guides pratiques pour les litiges fournisseurs", "intro": "Listes de contrôle pour les problèmes de non-livraison, de qualité, de spécification ou de remboursement Alibaba.", "read": "Lire le guide", "home": "Retour à ChinaTradeResolve", "note": "Information générale uniquement; les règles et délais des plateformes peuvent changer."},
    "de": {"title": "Praktische Leitfäden für Lieferantenstreitigkeiten", "intro": "Checklisten zu Nichtlieferung, Qualitätsmängeln, falschen Spezifikationen und Alibaba-Rückerstattungen.", "read": "Leitfaden lesen", "home": "Zurück zu ChinaTradeResolve", "note": "Nur allgemeine Information; Plattformregeln und Fristen können sich ändern."},
    "es": {"title": "Guías prácticas para disputas con proveedores", "intro": "Listas de comprobación para falta de entrega, problemas de calidad, especificaciones incorrectas y reembolsos de Alibaba.", "read": "Leer la guía", "home": "Volver a ChinaTradeResolve", "note": "Información general; las reglas y plazos de las plataformas pueden cambiar."},
    "sr": {"title": "Praktični vodiči za sporove sa dobavljačima", "intro": "Kontrolne liste za neisporuku, loš kvalitet, pogrešnu specifikaciju i Alibaba povraćaj novca.", "read": "Pročitaj vodič", "home": "Nazad na ChinaTradeResolve", "note": "Samo opšte informacije; pravila platforme i rokovi mogu da se promene."},
}

GUIDES = {
    "en": {
        "alibaba-dispute-evidence": {
            "title": "Alibaba dispute evidence checklist",
            "description": "A practical checklist for organizing order terms, supplier messages, payment records, inspection material and a clear refund request.",
            "intro": "A dispute is easier to review when every important statement is connected to a dated document, screenshot, photograph or video.",
            "sections": [
                ("1. Preserve the agreement", ["Save the Alibaba order, Trade Assurance terms, invoice, specification, drawings and approved samples.", "Export or screenshot messages showing what the supplier promised about material, dimensions, quality, quantity and shipment date."]),
                ("2. Build a dated chronology", ["List the agreement, payment, production updates, inspection, shipment and dispute events in order.", "Use exact dates and identify the source file for each event."]),
                ("3. Prove the problem", ["Use clear photographs and short videos. Include labels, packaging and scale where relevant.", "Compare the delivered or produced item directly with the written specification instead of relying on general statements such as ‘bad quality’." ]),
                ("4. State one consistent remedy", ["Specify whether you request a full refund, partial refund, replacement or cancellation.", "Explain how the amount was calculated and keep the request consistent across messages and forms."]),
            ],
            "mistakes": ["Deleting original files after making screenshots", "Submitting many duplicate images without captions", "Changing the main reason for the claim without explaining why", "Missing a platform deadline while negotiating privately"],
        },
        "supplier-not-shipped": {
            "title": "What to document when a Chinese supplier has not shipped",
            "description": "Evidence and timeline checklist for a paid order that was not shipped, was falsely marked as shipped or missed the agreed dispatch date.",
            "intro": "Separate a real shipment from a production update or a shipping label. The strongest file shows the agreed deadline, payment and the absence of verifiable dispatch.",
            "sections": [
                ("Confirm the contractual deadline", ["Save the order page, contract, pro forma invoice and messages confirming the dispatch date.", "Record any extensions and whether you accepted them."]),
                ("Check shipment evidence", ["Ask for the carrier name, tracking number, commercial invoice, packing list and handover receipt.", "A created label is not necessarily proof that the carrier received the goods."]),
                ("Preserve payment evidence", ["Keep the payment confirmation and the beneficiary details shown on the platform or invoice.", "Do not send additional money merely to unlock a promised refund."]),
                ("Act before deadlines", ["Use the platform dispute or refund procedure while it is available.", "Keep private negotiations concise and do not close a claim only because the supplier promises a later payment."]),
            ],
            "mistakes": ["Treating a tracking number with no carrier scan as proof of shipment", "Accepting repeated deadline extensions without written conditions", "Closing a dispute before funds arrive", "Failing to save the order page before it changes"],
        },
        "product-quality-dispute": {
            "title": "How to document a product quality or wrong-specification dispute",
            "description": "A structured way to compare the agreed specification with the produced or delivered goods and present objective evidence.",
            "intro": "Quality claims are strongest when the defect is measurable and tied to an agreed requirement.",
            "sections": [
                ("Define the agreed standard", ["Identify the exact clause, drawing, sample, material name, tolerance, colour, size or workmanship requirement.", "Save approvals and revisions so the final specification is clear."]),
                ("Capture objective evidence", ["Photograph the whole item and close-ups; use a ruler, scale or test result where appropriate.", "For repeated defects, show a representative sample and state how many units were checked."]),
                ("Connect each defect to the specification", ["Use a simple table: promised requirement, observed condition, source file and requested remedy.", "Avoid exaggeration and separate confirmed facts from suspicions that require testing."]),
                ("Preserve the goods and originals", ["Keep original photographs, videos, packaging, labels and inspection records.", "Do not alter or destroy potentially relevant evidence while the dispute is active."]),
            ],
            "mistakes": ["Using only emotional descriptions", "Claiming a material is fake without a reliable basis", "Showing defects without the agreed specification", "Mixing unrelated complaints into one unclear demand"],
        },
        "organize-dispute-documents": {
            "title": "How to organize documents for a supplier dispute",
            "description": "A folder structure and naming method that makes a supplier dispute easier to review by a platform, bank, insurer or adviser.",
            "intro": "Good organization does not create evidence, but it makes existing evidence easier to understand and harder to overlook.",
            "sections": [
                ("Create five folders", ["01 Agreement, 02 Payment, 03 Communications, 04 Production and delivery, 05 Problem and dispute.", "Keep originals unchanged and place working copies in a separate folder."]),
                ("Rename files consistently", ["Start with the date in YYYY-MM-DD format, followed by a short description.", "Example: 2026-07-15_supplier-confirms-nappa-leather.png."]),
                ("Make an evidence index", ["List each file, date, what it proves and the relevant claim.", "Flag missing documents and contradictions instead of hiding them."]),
                ("Prepare a one-page summary", ["State the parties, order, amount, central problem, chronology, remedy and urgent deadline.", "Link each important statement to an item in the evidence index."]),
            ],
            "mistakes": ["Renaming the only original file", "Combining hundreds of screenshots into an unreadable document", "Leaving screenshots without dates or context", "Submitting confidential data that is not relevant"],
        },
    },
    "ru": {
        "alibaba-dispute-evidence": {
            "title": "Чек-лист доказательств для спора на Alibaba",
            "description": "Как собрать условия заказа, переписку, оплату, материалы проверки и сформулировать понятное требование о возврате.",
            "intro": "Спор проще рассматривать, когда каждое важное утверждение подтверждено датированным документом, скриншотом, фотографией или видео.",
            "sections": [
                ("1. Сохраните договорённости", ["Скачайте заказ Alibaba, условия Trade Assurance, инвойс, спецификацию, чертежи и утверждённые образцы.", "Сохраните сообщения, где поставщик подтверждает материал, размеры, качество, количество и дату отправки."]),
                ("2. Составьте хронологию", ["Расположите по датам договорённости, оплату, производство, проверку, отгрузку и этапы спора.", "Для каждого события укажите файл-источник."]),
                ("3. Докажите проблему", ["Используйте чёткие фотографии и короткие видео; при необходимости покажите упаковку, маркировку и масштаб.", "Сопоставляйте товар с письменной спецификацией, а не ограничивайтесь формулировкой «плохое качество»." ]),
                ("4. Сформулируйте одно требование", ["Укажите: полный или частичный возврат, замена либо отмена заказа.", "Объясните расчёт суммы и придерживайтесь одной позиции во всех сообщениях."]),
            ],
            "mistakes": ["Удаление оригиналов после создания скриншотов", "Много одинаковых изображений без пояснений", "Смена главной причины спора без объяснения", "Пропуск срока площадки из-за частных переговоров"],
        },
        "supplier-not-shipped": {
            "title": "Что фиксировать, если китайский поставщик не отправил товар",
            "description": "Чек-лист для оплаченного заказа, который не отправлен, ложно отмечен как отправленный или просрочен.",
            "intro": "Нужно отличать реальную передачу груза перевозчику от сообщения о производстве или просто созданной транспортной накладной.",
            "sections": [
                ("Подтвердите срок", ["Сохраните заказ, договор, инвойс и сообщения с датой отгрузки.", "Зафиксируйте все переносы и своё согласие или несогласие."]),
                ("Проверьте доказательства отправки", ["Запросите перевозчика, трек-номер, коммерческий инвойс, упаковочный лист и подтверждение приёма груза.", "Созданная этикетка ещё не доказывает передачу товара перевозчику."]),
                ("Сохраните оплату", ["Храните платёжное подтверждение и реквизиты получателя из заказа или инвойса.", "Не переводите дополнительные деньги ради обещанного возврата."]),
                ("Не пропустите сроки", ["Используйте процедуру спора или возврата, пока она доступна.", "Не закрывайте спор только из-за обещания продавца вернуть деньги позднее."]),
            ],
            "mistakes": ["Считать трек без первого сканирования доказательством отправки", "Бесконечно соглашаться на переносы", "Закрыть спор до поступления денег", "Не сохранить страницу заказа до её изменения"],
        },
        "product-quality-dispute": {
            "title": "Как доказать брак или несоответствие спецификации",
            "description": "Структурированный способ сравнить согласованные требования с произведённым или полученным товаром.",
            "intro": "Претензия по качеству сильнее, когда дефект можно измерить и связать с конкретным согласованным требованием.",
            "sections": [
                ("Определите согласованный стандарт", ["Укажите пункт спецификации, чертёж, образец, материал, допуск, цвет, размер или требование к пошиву.", "Сохраните утверждения и изменения, чтобы была понятна финальная версия."]),
                ("Снимите объективные доказательства", ["Сфотографируйте изделие целиком и крупным планом; при необходимости используйте линейку, весы или результат теста.", "При массовом браке покажите выборку и укажите количество проверенных единиц."]),
                ("Свяжите дефект с условием", ["Сделайте таблицу: обещанное требование, фактическое состояние, файл и требование покупателя.", "Отделяйте подтверждённые факты от предположений, для которых нужна экспертиза."]),
                ("Сохраните товар и оригиналы", ["Не удаляйте исходные фото, видео, упаковку, этикетки и акты проверки.", "Не изменяйте доказательства, пока спор продолжается."]),
            ],
            "mistakes": ["Только эмоциональное описание", "Утверждение о подделке материала без надёжного основания", "Фото дефекта без согласованной спецификации", "Смешивание нескольких разных требований"],
        },
        "organize-dispute-documents": {
            "title": "Как организовать документы по спору с поставщиком",
            "description": "Структура папок и названий файлов для понятного рассмотрения площадкой, банком, страховщиком или консультантом.",
            "intro": "Хорошая организация не создаёт доказательства, но помогает быстро понять уже имеющиеся материалы.",
            "sections": [
                ("Создайте пять папок", ["01 Договорённости, 02 Оплата, 03 Переписка, 04 Производство и доставка, 05 Проблема и спор.", "Оригиналы храните неизменными, рабочие копии — отдельно."]),
                ("Переименуйте файлы единообразно", ["Начинайте с даты в формате ГГГГ-ММ-ДД и короткого описания.", "Пример: 2026-07-15_postavshchik-podtverdil-kozhu-nappa.png."]),
                ("Составьте индекс доказательств", ["Для каждого файла укажите дату, содержание, что он подтверждает и к какому требованию относится.", "Отмечайте пробелы и противоречия, а не скрывайте их."]),
                ("Подготовьте резюме на одну страницу", ["Укажите стороны, заказ, сумму, главную проблему, хронологию, требование и срочный срок.", "Свяжите каждое важное утверждение с номером доказательства."]),
            ],
            "mistakes": ["Переименование единственного оригинала", "Сотни скриншотов в одном нечитаемом файле", "Скриншоты без дат и контекста", "Передача лишних конфиденциальных данных"],
        },
    },
}

GUIDE_CARD_COPY = {
    "en": {slug: {"title": data["title"], "description": data["description"]} for slug, data in GUIDES["en"].items()},
    "ru": {slug: {"title": data["title"], "description": data["description"]} for slug, data in GUIDES["ru"].items()},
    "fr": {
        "alibaba-dispute-evidence": {"title": "Liste de preuves pour un litige Alibaba", "description": "Organiser contrat, messages, paiement, preuves du problème et demande de remboursement."},
        "supplier-not-shipped": {"title": "Le fournisseur chinois n’a pas expédié", "description": "Que conserver lorsqu’une commande payée n’a pas été réellement remise au transporteur."},
        "product-quality-dispute": {"title": "Défaut de qualité ou mauvaise spécification", "description": "Comparer objectivement l’accord et les produits fabriqués ou livrés."},
        "organize-dispute-documents": {"title": "Organiser les documents du litige", "description": "Dossiers, noms de fichiers, chronologie et index des preuves."},
    },
    "de": {
        "alibaba-dispute-evidence": {"title": "Beweis-Checkliste für Alibaba-Streitfälle", "description": "Vertrag, Nachrichten, Zahlung, Problemdokumentation und Erstattungsforderung ordnen."},
        "supplier-not-shipped": {"title": "Chinesischer Lieferant hat nicht versandt", "description": "Welche Nachweise bei einer bezahlten, aber nicht übergebenen Sendung wichtig sind."},
        "product-quality-dispute": {"title": "Qualitätsmangel oder falsche Spezifikation", "description": "Vereinbarung und hergestellte oder gelieferte Ware objektiv vergleichen."},
        "organize-dispute-documents": {"title": "Streitunterlagen organisieren", "description": "Ordner, Dateinamen, Chronologie und Beweisverzeichnis."},
    },
    "es": {
        "alibaba-dispute-evidence": {"title": "Lista de pruebas para una disputa de Alibaba", "description": "Organizar contrato, mensajes, pago, pruebas del problema y solicitud de reembolso."},
        "supplier-not-shipped": {"title": "El proveedor chino no envió el pedido", "description": "Qué conservar cuando un pedido pagado no fue entregado realmente al transportista."},
        "product-quality-dispute": {"title": "Problema de calidad o especificación incorrecta", "description": "Comparar de forma objetiva lo acordado con el producto fabricado o entregado."},
        "organize-dispute-documents": {"title": "Organizar los documentos de la disputa", "description": "Carpetas, nombres de archivo, cronología e índice de pruebas."},
    },
    "sr": {
        "alibaba-dispute-evidence": {"title": "Kontrolna lista dokaza za Alibaba spor", "description": "Organizujte ugovor, poruke, plaćanje, dokaz problema i zahtev za povraćaj."},
        "supplier-not-shipped": {"title": "Kineski dobavljač nije poslao robu", "description": "Šta sačuvati kada plaćena porudžbina nije stvarno predata prevozniku."},
        "product-quality-dispute": {"title": "Loš kvalitet ili pogrešna specifikacija", "description": "Objektivno uporedite dogovoreno sa proizvedenom ili isporučenom robom."},
        "organize-dispute-documents": {"title": "Organizovanje dokumenata za spor", "description": "Fascikle, nazivi fajlova, hronologija i indeks dokaza."},
    },
}

# Full multilingual guide content and shared detail-page labels (v3.7.35).
GUIDES.update({'fr': {'alibaba-dispute-evidence': {'title': 'Liste de preuves pour un litige Alibaba',
                                     'description': 'Comment rassembler les conditions de commande, les messages, le '
                                                    'paiement, les contrôles et une demande de remboursement claire.',
                                     'intro': 'Un litige est plus facile à examiner lorsque chaque affirmation '
                                              'importante est reliée à un document, une capture, une photo ou une '
                                              'vidéo datée.',
                                     'sections': [('1. Conservez les accords',
                                                   ['Téléchargez la commande Alibaba, les conditions Trade Assurance, '
                                                    'la facture, les spécifications, les plans et les échantillons '
                                                    'approuvés.',
                                                    'Conservez les messages où le fournisseur confirme le matériau, '
                                                    'les dimensions, la qualité, la quantité et la date '
                                                    'd’expédition.']),
                                                  ('2. Établissez une chronologie',
                                                   ['Classez par date les accords, le paiement, la production, '
                                                    'l’inspection, l’expédition et les étapes du litige.',
                                                    'Pour chaque événement, indiquez le fichier qui le prouve.']),
                                                  ('3. Prouvez le problème',
                                                   ['Utilisez des photos nettes et de courtes vidéos ; montrez si '
                                                    'nécessaire l’emballage, les étiquettes et une référence '
                                                    'd’échelle.',
                                                    'Comparez le produit à la spécification écrite au lieu de vous '
                                                    'limiter à « mauvaise qualité ».']),
                                                  ('4. Formulez une seule demande',
                                                   ['Précisez s’il s’agit d’un remboursement total ou partiel, d’un '
                                                    'remplacement ou d’une annulation.',
                                                    'Expliquez le calcul du montant et gardez la même position dans '
                                                    'tous les messages.'])],
                                     'mistakes': ['Supprimer les originaux après avoir créé des captures',
                                                  'Joindre de nombreuses images identiques sans explication',
                                                  'Changer le motif principal du litige sans l’expliquer',
                                                  'Laisser expirer un délai de la plateforme pendant des négociations '
                                                  'privées']},
        'supplier-not-shipped': {'title': 'Que conserver si le fournisseur chinois n’a pas expédié',
                                 'description': 'Liste de contrôle pour une commande payée non expédiée, faussement '
                                                'marquée comme expédiée ou en retard.',
                                 'intro': 'Il faut distinguer la remise réelle au transporteur d’un message sur la '
                                          'production ou de la simple création d’une étiquette d’envoi.',
                                 'sections': [('Confirmez la date prévue',
                                               ['Conservez la commande, le contrat, la facture et les messages '
                                                'indiquant la date d’expédition.',
                                                'Notez chaque report ainsi que votre accord ou votre refus.']),
                                              ('Vérifiez la preuve d’expédition',
                                               ['Demandez le nom du transporteur, le numéro de suivi, la facture '
                                                'commerciale, la liste de colisage et la preuve de prise en charge.',
                                                'Une étiquette créée ne prouve pas que la marchandise a été remise au '
                                                'transporteur.']),
                                              ('Conservez la preuve du paiement',
                                               ['Gardez la confirmation de paiement et les coordonnées du bénéficiaire '
                                                'figurant dans la commande ou la facture.',
                                                'Ne versez pas d’argent supplémentaire en échange d’une promesse de '
                                                'remboursement.']),
                                              ('Ne manquez pas les délais',
                                               ['Utilisez la procédure de litige ou de remboursement tant qu’elle est '
                                                'encore disponible.',
                                                'Ne fermez pas le litige uniquement parce que le vendeur promet de '
                                                'rembourser plus tard.'])],
                                 'mistakes': ['Considérer un numéro de suivi sans premier scan comme une preuve '
                                              'd’expédition',
                                              'Accepter indéfiniment de nouveaux reports',
                                              'Fermer le litige avant réception effective des fonds',
                                              'Ne pas sauvegarder la page de commande avant sa modification']},
        'product-quality-dispute': {'title': 'Comment prouver un défaut ou une mauvaise spécification',
                                    'description': 'Une méthode structurée pour comparer les exigences convenues au '
                                                   'produit fabriqué ou reçu.',
                                    'intro': 'Une réclamation qualité est plus solide lorsque le défaut est mesurable '
                                             'et relié à une exigence convenue précise.',
                                    'sections': [('Identifiez la norme convenue',
                                                  ['Citez la clause, le plan, l’échantillon, le matériau, la '
                                                   'tolérance, la couleur, la dimension ou l’exigence de fabrication '
                                                   'concernée.',
                                                   'Conservez les validations et modifications afin d’identifier la '
                                                   'version finale.']),
                                                 ('Créez des preuves objectives',
                                                  ['Photographiez le produit en entier puis en gros plan ; utilisez si '
                                                   'nécessaire une règle, une balance ou un résultat de test.',
                                                   'Pour un défaut de série, montrez un échantillon et indiquez le '
                                                   'nombre d’unités contrôlées.']),
                                                 ('Reliez le défaut à l’accord',
                                                  ['Créez un tableau : exigence promise, état réel, fichier de preuve '
                                                   'et demande de l’acheteur.',
                                                   'Séparez les faits confirmés des hypothèses qui nécessitent une '
                                                   'expertise.']),
                                                 ('Conservez le produit et les originaux',
                                                  ['Ne supprimez pas les photos, vidéos, emballages, étiquettes ni '
                                                   'rapports d’inspection originaux.',
                                                   'Ne modifiez pas les preuves pendant que le litige est en cours.'])],
                                    'mistakes': ['Utiliser uniquement une description émotionnelle',
                                                 'Affirmer qu’un matériau est faux sans base fiable',
                                                 'Montrer un défaut sans joindre la spécification convenue',
                                                 'Mélanger plusieurs demandes différentes dans une seule affirmation']},
        'organize-dispute-documents': {'title': 'Comment organiser les documents d’un litige fournisseur',
                                       'description': 'Une structure de dossiers et de noms de fichiers pour faciliter '
                                                      'l’examen par une plateforme, une banque, un assureur ou un '
                                                      'conseiller.',
                                       'intro': 'Une bonne organisation ne crée pas de preuve, mais elle permet de '
                                                'comprendre rapidement les documents déjà disponibles.',
                                       'sections': [('Créez cinq dossiers',
                                                     ['01 Accords, 02 Paiement, 03 Messages, 04 Production et '
                                                      'livraison, 05 Problème et litige.',
                                                      'Conservez les originaux sans modification et les copies de '
                                                      'travail séparément.']),
                                                    ('Nommez les fichiers de manière uniforme',
                                                     ['Commencez par la date au format AAAA-MM-JJ, suivie d’une courte '
                                                      'description.',
                                                      'Exemple : 2026-07-15_fournisseur-confirme-cuir-nappa.png.']),
                                                    ('Créez un index des preuves',
                                                     ['Pour chaque fichier, indiquez la date, le contenu, ce qu’il '
                                                      'prouve et la demande concernée.',
                                                      'Signalez les documents manquants et les contradictions au lieu '
                                                      'de les masquer.']),
                                                    ('Préparez un résumé d’une page',
                                                     ['Indiquez les parties, la commande, le montant, le problème '
                                                      'central, la chronologie, la demande et le délai urgent.',
                                                      'Reliez chaque affirmation importante à un numéro de preuve.'])],
                                       'mistakes': ['Renommer l’unique fichier original',
                                                    'Regrouper des centaines de captures dans un document illisible',
                                                    'Conserver des captures sans date ni contexte',
                                                    'Transmettre des données confidentielles sans rapport avec le '
                                                    'litige']}},
 'de': {'alibaba-dispute-evidence': {'title': 'Beweis-Checkliste für einen Alibaba-Streitfall',
                                     'description': 'Bestellbedingungen, Nachrichten, Zahlung, Prüfunterlagen und eine '
                                                    'klare Erstattungsforderung richtig zusammenstellen.',
                                     'intro': 'Ein Streitfall lässt sich leichter prüfen, wenn jede wichtige Aussage '
                                              'mit einem datierten Dokument, Screenshot, Foto oder Video belegt ist.',
                                     'sections': [('1. Vereinbarungen sichern',
                                                   ['Laden Sie die Alibaba-Bestellung, Trade-Assurance-Bedingungen, '
                                                    'Rechnung, Spezifikation, Zeichnungen und freigegebenen Muster '
                                                    'herunter.',
                                                    'Sichern Sie Nachrichten, in denen der Lieferant Material, Maße, '
                                                    'Qualität, Menge und Versanddatum bestätigt.']),
                                                  ('2. Eine Chronologie erstellen',
                                                   ['Ordnen Sie Vereinbarungen, Zahlung, Produktion, Prüfung, Versand '
                                                    'und Streitfall-Schritte nach Datum.',
                                                    'Nennen Sie zu jedem Ereignis die zugehörige Quelldatei.']),
                                                  ('3. Das Problem belegen',
                                                   ['Verwenden Sie klare Fotos und kurze Videos; zeigen Sie bei Bedarf '
                                                    'Verpackung, Kennzeichnung und einen Größenvergleich.',
                                                    'Vergleichen Sie die Ware mit der schriftlichen Spezifikation, '
                                                    'statt nur von „schlechter Qualität“ zu sprechen.']),
                                                  ('4. Eine eindeutige Forderung stellen',
                                                   ['Geben Sie an, ob Sie vollständige oder teilweise Erstattung, '
                                                    'Ersatz oder Stornierung verlangen.',
                                                    'Erklären Sie die Berechnung und vertreten Sie in allen '
                                                    'Nachrichten dieselbe Position.'])],
                                     'mistakes': ['Originale nach dem Erstellen von Screenshots löschen',
                                                  'Viele identische Bilder ohne Erläuterung einreichen',
                                                  'Den Hauptgrund des Streitfalls ohne Erklärung wechseln',
                                                  'Eine Plattformfrist wegen privater Verhandlungen verpassen']},
        'supplier-not-shipped': {'title': 'Was festzuhalten ist, wenn der chinesische Lieferant nicht versendet',
                                 'description': 'Checkliste für eine bezahlte Bestellung, die nicht versandt, falsch '
                                                'als versandt markiert oder verspätet ist.',
                                 'intro': 'Eine tatsächliche Übergabe an den Frachtführer muss von einer '
                                          'Produktionsmeldung oder nur erstellten Versandmarke unterschieden werden.',
                                 'sections': [('Versandtermin bestätigen',
                                               ['Sichern Sie Bestellung, Vertrag, Rechnung und Nachrichten mit dem '
                                                'zugesagten Versanddatum.',
                                                'Dokumentieren Sie jede Verschiebung sowie Ihre Zustimmung oder '
                                                'Ablehnung.']),
                                              ('Versandnachweis prüfen',
                                               ['Fordern Sie Frachtführer, Sendungsnummer, Handelsrechnung, Packliste '
                                                'und Übernahmebestätigung an.',
                                                'Eine erstellte Versandmarke beweist noch keine Übergabe der Ware an '
                                                'den Frachtführer.']),
                                              ('Zahlung sichern',
                                               ['Bewahren Sie den Zahlungsbeleg und die Empfängerdaten aus Bestellung '
                                                'oder Rechnung auf.',
                                                'Überweisen Sie kein zusätzliches Geld im Austausch für eine '
                                                'versprochene Rückerstattung.']),
                                              ('Fristen nicht verpassen',
                                               ['Nutzen Sie das Streit- oder Erstattungsverfahren, solange es noch '
                                                'verfügbar ist.',
                                                'Schließen Sie den Streitfall nicht nur wegen eines späteren '
                                                'Rückzahlungsversprechens des Verkäufers.'])],
                                 'mistakes': ['Eine Sendungsnummer ohne ersten Scan als Versandnachweis ansehen',
                                              'Unbegrenzt weiteren Verschiebungen zustimmen',
                                              'Den Streitfall vor dem tatsächlichen Geldeingang schließen',
                                              'Die Bestellseite vor Änderungen nicht sichern']},
        'product-quality-dispute': {'title': 'Mängel oder Abweichungen von der Spezifikation nachweisen',
                                    'description': 'Eine strukturierte Methode zum Vergleich der vereinbarten '
                                                   'Anforderungen mit der hergestellten oder gelieferten Ware.',
                                    'intro': 'Eine Qualitätsreklamation ist stärker, wenn der Mangel messbar ist und '
                                             'mit einer konkreten vereinbarten Anforderung verbunden wird.',
                                    'sections': [('Vereinbarten Standard bestimmen',
                                                  ['Nennen Sie Klausel, Zeichnung, Muster, Material, Toleranz, Farbe, '
                                                   'Maß oder Verarbeitungsanforderung.',
                                                   'Sichern Sie Freigaben und Änderungen, damit die endgültige Version '
                                                   'erkennbar ist.']),
                                                 ('Objektive Beweise erstellen',
                                                  ['Fotografieren Sie die Ware vollständig und im Detail; verwenden '
                                                   'Sie bei Bedarf Lineal, Waage oder Testergebnis.',
                                                   'Bei Serienmängeln zeigen Sie eine Stichprobe und nennen die Zahl '
                                                   'der geprüften Einheiten.']),
                                                 ('Mangel mit der Vereinbarung verknüpfen',
                                                  ['Erstellen Sie eine Tabelle: zugesagte Anforderung, tatsächlicher '
                                                   'Zustand, Beweisdatei und Forderung des Käufers.',
                                                   'Trennen Sie bestätigte Tatsachen von Annahmen, die eine fachliche '
                                                   'Prüfung erfordern.']),
                                                 ('Ware und Originale aufbewahren',
                                                  ['Löschen Sie keine Originalfotos, Videos, Verpackungen, Etiketten '
                                                   'oder Prüfberichte.',
                                                   'Verändern Sie Beweismittel nicht, solange der Streitfall läuft.'])],
                                    'mistakes': ['Nur emotional beschreiben',
                                                 'Ein gefälschtes Material ohne belastbare Grundlage behaupten',
                                                 'Mängelfotos ohne vereinbarte Spezifikation vorlegen',
                                                 'Mehrere unterschiedliche Forderungen vermischen']},
        'organize-dispute-documents': {'title': 'Unterlagen für einen Lieferantenstreit organisieren',
                                       'description': 'Ordner- und Dateinamensstruktur für eine verständliche Prüfung '
                                                      'durch Plattform, Bank, Versicherer oder Berater.',
                                       'intro': 'Gute Organisation schafft keine neuen Beweise, macht vorhandene '
                                                'Unterlagen aber schnell verständlich.',
                                       'sections': [('Fünf Ordner anlegen',
                                                     ['01 Vereinbarungen, 02 Zahlung, 03 Nachrichten, 04 Produktion '
                                                      'und Lieferung, 05 Problem und Streitfall.',
                                                      'Bewahren Sie Originale unverändert und Arbeitskopien getrennt '
                                                      'auf.']),
                                                    ('Dateien einheitlich benennen',
                                                     ['Beginnen Sie mit dem Datum im Format JJJJ-MM-TT und einer '
                                                      'kurzen Beschreibung.',
                                                      'Beispiel: 2026-07-15_lieferant-bestaetigt-nappaleder.png.']),
                                                    ('Beweisverzeichnis erstellen',
                                                     ['Nennen Sie zu jeder Datei Datum, Inhalt, Beweiswert und '
                                                      'zugehörige Forderung.',
                                                      'Kennzeichnen Sie fehlende Unterlagen und Widersprüche, statt '
                                                      'sie zu verbergen.']),
                                                    ('Einseitige Zusammenfassung vorbereiten',
                                                     ['Nennen Sie Parteien, Bestellung, Betrag, Kernproblem, '
                                                      'Chronologie, Forderung und dringende Frist.',
                                                      'Verknüpfen Sie jede wichtige Aussage mit einer Beweisnummer.'])],
                                       'mistakes': ['Die einzige Originaldatei umbenennen',
                                                    'Hunderte Screenshots in einem unlesbaren Dokument zusammenfassen',
                                                    'Screenshots ohne Datum oder Kontext behalten',
                                                    'Nicht erforderliche vertrauliche Daten weitergeben']}},
 'es': {'alibaba-dispute-evidence': {'title': 'Lista de pruebas para una disputa de Alibaba',
                                     'description': 'Cómo reunir condiciones del pedido, mensajes, pago, inspecciones '
                                                    'y una solicitud de reembolso clara.',
                                     'intro': 'Una disputa es más fácil de revisar cuando cada afirmación importante '
                                              'está vinculada a un documento, captura, fotografía o vídeo con fecha.',
                                     'sections': [('1. Guarde los acuerdos',
                                                   ['Descargue el pedido de Alibaba, las condiciones de Trade '
                                                    'Assurance, la factura, la especificación, los planos y las '
                                                    'muestras aprobadas.',
                                                    'Conserve los mensajes donde el proveedor confirma material, '
                                                    'medidas, calidad, cantidad y fecha de envío.']),
                                                  ('2. Prepare una cronología',
                                                   ['Ordene por fecha los acuerdos, el pago, la producción, la '
                                                    'inspección, el envío y los pasos de la disputa.',
                                                    'Para cada hecho, indique el archivo que lo respalda.']),
                                                  ('3. Demuestre el problema',
                                                   ['Utilice fotografías claras y vídeos cortos; muestre el embalaje, '
                                                    'las etiquetas y una referencia de escala cuando sea necesario.',
                                                    'Compare el producto con la especificación escrita en lugar de '
                                                    'limitarse a decir «mala calidad».']),
                                                  ('4. Formule una sola solicitud',
                                                   ['Indique si solicita reembolso total o parcial, sustitución o '
                                                    'cancelación.',
                                                    'Explique el cálculo del importe y mantenga la misma posición en '
                                                    'todos los mensajes.'])],
                                     'mistakes': ['Eliminar los originales después de crear capturas',
                                                  'Enviar muchas imágenes iguales sin explicación',
                                                  'Cambiar el motivo principal de la disputa sin explicarlo',
                                                  'Perder un plazo de la plataforma por negociaciones privadas']},
        'supplier-not-shipped': {'title': 'Qué conservar si el proveedor chino no envió el pedido',
                                 'description': 'Lista de control para un pedido pagado que no fue enviado, aparece '
                                                'falsamente como enviado o está retrasado.',
                                 'intro': 'Hay que distinguir la entrega real al transportista de un mensaje sobre '
                                          'producción o de una etiqueta de envío simplemente creada.',
                                 'sections': [('Confirme la fecha de envío',
                                               ['Guarde el pedido, el contrato, la factura y los mensajes con la fecha '
                                                'de envío prometida.',
                                                'Registre cada aplazamiento y si lo aceptó o rechazó.']),
                                              ('Compruebe la prueba de envío',
                                               ['Solicite transportista, número de seguimiento, factura comercial, '
                                                'lista de embalaje y comprobante de recepción de la carga.',
                                                'Una etiqueta creada no demuestra que la mercancía haya sido entregada '
                                                'al transportista.']),
                                              ('Conserve el pago',
                                               ['Guarde el comprobante de pago y los datos del beneficiario que '
                                                'figuran en el pedido o la factura.',
                                                'No envíe dinero adicional a cambio de una promesa de reembolso.']),
                                              ('No pierda los plazos',
                                               ['Utilice el procedimiento de disputa o reembolso mientras siga '
                                                'disponible.',
                                                'No cierre la disputa solo porque el vendedor promete devolver el '
                                                'dinero más tarde.'])],
                                 'mistakes': ['Tratar un seguimiento sin primer escaneo como prueba de envío',
                                              'Aceptar aplazamientos de manera indefinida',
                                              'Cerrar la disputa antes de recibir realmente el dinero',
                                              'No guardar la página del pedido antes de que cambie']},
        'product-quality-dispute': {'title': 'Cómo demostrar defectos o incumplimiento de especificaciones',
                                    'description': 'Una forma estructurada de comparar los requisitos acordados con el '
                                                   'producto fabricado o recibido.',
                                    'intro': 'Una reclamación de calidad es más sólida cuando el defecto se puede '
                                             'medir y se vincula a un requisito concreto acordado.',
                                    'sections': [('Identifique el estándar acordado',
                                                  ['Cite la cláusula, plano, muestra, material, tolerancia, color, '
                                                   'medida o requisito de fabricación correspondiente.',
                                                   'Guarde aprobaciones y cambios para dejar clara la versión final.']),
                                                 ('Cree pruebas objetivas',
                                                  ['Fotografíe el producto completo y en detalle; use una regla, una '
                                                   'báscula o un resultado de prueba cuando sea necesario.',
                                                   'Si el defecto es masivo, muestre una muestra e indique cuántas '
                                                   'unidades fueron revisadas.']),
                                                 ('Vincule el defecto al acuerdo',
                                                  ['Prepare una tabla: requisito prometido, estado real, archivo de '
                                                   'prueba y solicitud del comprador.',
                                                   'Separe los hechos confirmados de las hipótesis que requieren una '
                                                   'evaluación técnica.']),
                                                 ('Conserve el producto y los originales',
                                                  ['No elimine fotografías, vídeos, embalajes, etiquetas ni informes '
                                                   'de inspección originales.',
                                                   'No altere las pruebas mientras la disputa siga abierta.'])],
                                    'mistakes': ['Usar solo una descripción emocional',
                                                 'Afirmar que el material es falso sin una base fiable',
                                                 'Mostrar el defecto sin adjuntar la especificación acordada',
                                                 'Mezclar varias solicitudes diferentes']},
        'organize-dispute-documents': {'title': 'Cómo organizar los documentos de una disputa con un proveedor',
                                       'description': 'Estructura de carpetas y nombres de archivo para una revisión '
                                                      'clara por una plataforma, banco, aseguradora o asesor.',
                                       'intro': 'Una buena organización no crea pruebas, pero permite entender '
                                                'rápidamente los materiales que ya existen.',
                                       'sections': [('Cree cinco carpetas',
                                                     ['01 Acuerdos, 02 Pago, 03 Mensajes, 04 Producción y entrega, 05 '
                                                      'Problema y disputa.',
                                                      'Mantenga los originales sin cambios y las copias de trabajo por '
                                                      'separado.']),
                                                    ('Nombre los archivos de forma uniforme',
                                                     ['Empiece por la fecha en formato AAAA-MM-DD y añada una '
                                                      'descripción corta.',
                                                      'Ejemplo: 2026-07-15_proveedor-confirma-cuero-nappa.png.']),
                                                    ('Prepare un índice de pruebas',
                                                     ['Para cada archivo, indique fecha, contenido, qué demuestra y a '
                                                      'qué solicitud se refiere.',
                                                      'Marque los documentos faltantes y las contradicciones en lugar '
                                                      'de ocultarlos.']),
                                                    ('Prepare un resumen de una página',
                                                     ['Indique partes, pedido, importe, problema central, cronología, '
                                                      'solicitud y plazo urgente.',
                                                      'Vincule cada afirmación importante con un número de prueba.'])],
                                       'mistakes': ['Cambiar el nombre del único archivo original',
                                                    'Combinar cientos de capturas en un documento ilegible',
                                                    'Guardar capturas sin fecha ni contexto',
                                                    'Enviar datos confidenciales que no son necesarios']}},
 'sr': {'alibaba-dispute-evidence': {'title': 'Kontrolna lista dokaza za Alibaba spor',
                                     'description': 'Kako prikupiti uslove porudžbine, poruke, dokaz o plaćanju, '
                                                    'rezultate kontrole i jasan zahtev za povraćaj.',
                                     'intro': 'Spor je lakše pregledati kada je svaka važna tvrdnja povezana sa '
                                              'datiranim dokumentom, snimkom ekrana, fotografijom ili video-zapisom.',
                                     'sections': [('1. Sačuvajte dogovorene uslove',
                                                   ['Preuzmite Alibaba porudžbinu, Trade Assurance uslove, fakturu, '
                                                    'specifikaciju, crteže i odobrene uzorke.',
                                                    'Sačuvajte poruke u kojima dobavljač potvrđuje materijal, '
                                                    'dimenzije, kvalitet, količinu i datum slanja.']),
                                                  ('2. Napravite hronologiju',
                                                   ['Poređajte po datumima dogovor, plaćanje, proizvodnju, kontrolu, '
                                                    'slanje i korake u sporu.',
                                                    'Za svaki događaj navedite izvorni fajl.']),
                                                  ('3. Dokažite problem',
                                                   ['Koristite jasne fotografije i kratke video-zapise; po potrebi '
                                                    'pokažite ambalažu, oznake i merilo.',
                                                    'Uporedite robu sa pisanom specifikacijom umesto da navedete samo '
                                                    '„loš kvalitet“.']),
                                                  ('4. Postavite jedan jasan zahtev',
                                                   ['Navedite da li tražite potpun ili delimičan povraćaj, zamenu ili '
                                                    'otkazivanje porudžbine.',
                                                    'Objasnite obračun iznosa i zadržite isti stav u svim porukama.'])],
                                     'mistakes': ['Brisanje originala nakon pravljenja snimaka ekrana',
                                                  'Slanje mnogo istih fotografija bez objašnjenja',
                                                  'Menjanje glavnog razloga spora bez objašnjenja',
                                                  'Propuštanje roka platforme zbog privatnih pregovora']},
        'supplier-not-shipped': {'title': 'Šta sačuvati ako kineski dobavljač nije poslao robu',
                                 'description': 'Kontrolna lista za plaćenu porudžbinu koja nije poslata, pogrešno je '
                                                'označena kao poslata ili kasni.',
                                 'intro': 'Stvarnu predaju robe prevozniku treba razlikovati od poruke o proizvodnji '
                                          'ili samo kreirane transportne etikete.',
                                 'sections': [('Potvrdite rok slanja',
                                               ['Sačuvajte porudžbinu, ugovor, fakturu i poruke sa dogovorenim datumom '
                                                'slanja.',
                                                'Zabeležite svako odlaganje i da li ste ga prihvatili ili odbili.']),
                                              ('Proverite dokaz o slanju',
                                               ['Tražite naziv prevoznika, broj za praćenje, komercijalnu fakturu, '
                                                'listu pakovanja i potvrdu prijema tereta.',
                                                'Kreirana etiketa ne dokazuje da je roba predata prevozniku.']),
                                              ('Sačuvajte dokaz o uplati',
                                               ['Čuvajte potvrdu o plaćanju i podatke primaoca iz porudžbine ili '
                                                'fakture.',
                                                'Ne šaljite dodatni novac u zamenu za obećani povraćaj.']),
                                              ('Ne propustite rokove',
                                               ['Koristite postupak spora ili povraćaja dok je još dostupan.',
                                                'Ne zatvarajte spor samo zato što prodavac obećava kasniji '
                                                'povraćaj.'])],
                                 'mistakes': ['Smatrati broj za praćenje bez prvog skeniranja dokazom slanja',
                                              'Neograničeno prihvatati nova odlaganja',
                                              'Zatvoriti spor pre stvarnog prijema novca',
                                              'Ne sačuvati stranicu porudžbine pre izmene']},
        'product-quality-dispute': {'title': 'Kako dokazati nedostatak ili odstupanje od specifikacije',
                                    'description': 'Strukturisan način da uporedite dogovorene zahteve sa proizvedenom '
                                                   'ili primljenom robom.',
                                    'intro': 'Reklamacija kvaliteta je jača kada se nedostatak može izmeriti i '
                                             'povezati sa konkretnim dogovorenim zahtevom.',
                                    'sections': [('Odredite dogovoreni standard',
                                                  ['Navedite odredbu, crtež, uzorak, materijal, toleranciju, boju, '
                                                   'dimenziju ili zahtev obrade.',
                                                   'Sačuvajte odobrenja i izmene kako bi konačna verzija bila jasna.']),
                                                 ('Napravite objektivne dokaze',
                                                  ['Fotografišite ceo proizvod i detalje; po potrebi koristite lenjir, '
                                                   'vagu ili rezultat testa.',
                                                   'Ako je problem serijski, pokažite uzorak i navedite koliko je '
                                                   'jedinica pregledano.']),
                                                 ('Povežite nedostatak sa dogovorom',
                                                  ['Napravite tabelu: obećani zahtev, stvarno stanje, dokazni fajl i '
                                                   'zahtev kupca.',
                                                   'Odvojite potvrđene činjenice od pretpostavki za koje je potrebna '
                                                   'stručna provera.']),
                                                 ('Sačuvajte robu i originale',
                                                  ['Ne brišite originalne fotografije, video-zapise, ambalažu, etikete '
                                                   'ni izveštaje kontrole.',
                                                   'Ne menjajte dokaze dok spor traje.'])],
                                    'mistakes': ['Samo emotivan opis problema',
                                                 'Tvrdnja o lažnom materijalu bez pouzdane osnove',
                                                 'Fotografije nedostatka bez dogovorene specifikacije',
                                                 'Mešanje više različitih zahteva']},
        'organize-dispute-documents': {'title': 'Kako organizovati dokumenta za spor sa dobavljačem',
                                       'description': 'Struktura fascikli i naziva fajlova za jasan pregled platforme, '
                                                      'banke, osiguravača ili savetnika.',
                                       'intro': 'Dobra organizacija ne stvara nove dokaze, ali omogućava da se '
                                                'postojeći materijal brzo razume.',
                                       'sections': [('Napravite pet fascikli',
                                                     ['01 Dogovor, 02 Plaćanje, 03 Poruke, 04 Proizvodnja i isporuka, '
                                                      '05 Problem i spor.',
                                                      'Originale čuvajte neizmenjene, a radne kopije odvojeno.']),
                                                    ('Ujednačeno imenujte fajlove',
                                                     ['Počnite datumom u formatu GGGG-MM-DD i dodajte kratak opis.',
                                                      'Primer: 2026-07-15_dobavljac-potvrdio-nappa-kozu.png.']),
                                                    ('Napravite indeks dokaza',
                                                     ['Za svaki fajl navedite datum, sadržaj, šta dokazuje i na koji '
                                                      'zahtev se odnosi.',
                                                      'Označite šta nedostaje i gde postoje protivrečnosti umesto da '
                                                      'ih sakrijete.']),
                                                    ('Pripremite sažetak na jednoj strani',
                                                     ['Navedite strane, porudžbinu, iznos, glavni problem, '
                                                      'hronologiju, zahtev i hitan rok.',
                                                      'Povežite svaku važnu tvrdnju sa brojem dokaza.'])],
                                       'mistakes': ['Preimenovanje jedinog originalnog fajla',
                                                    'Spajanje stotina snimaka ekrana u nečitljiv dokument',
                                                    'Snimci ekrana bez datuma ili konteksta',
                                                    'Slanje poverljivih podataka koji nisu relevantni']}}})

GUIDE_DETAIL_COPY = {'en': {'all_guides': 'All guides',
        'common_mistakes': 'Common mistakes',
        'cta_title': 'Need a preliminary review of your case?',
        'cta_body': 'Describe the situation and identify the documents you already have. Do not put confidential '
                    'documents in the public chat.',
        'cta_button': 'Open the application form',
        'fine': 'Educational information, not legal advice. Check current platform rules and deadlines.',
        'updated': 'Updated 24 July 2026',
        'related': 'Related guides',
        'home': 'Home'},
 'ru': {'all_guides': 'Все руководства',
        'common_mistakes': 'Частые ошибки',
        'cta_title': 'Нужна предварительная оценка вашего дела?',
        'cta_body': 'Опишите ситуацию и укажите, какие документы уже есть. Не отправляйте конфиденциальные материалы в '
                    'публичный чат.',
        'cta_button': 'Перейти к заявке',
        'fine': 'Информационный материал, не юридическая консультация. Проверяйте актуальные правила площадки и сроки.',
        'updated': 'Обновлено 24 июля 2026 года',
        'related': 'Другие руководства',
        'home': 'Главная'},
 'fr': {'all_guides': 'Tous les guides',
        'common_mistakes': 'Erreurs fréquentes',
        'cta_title': 'Besoin d’une évaluation préliminaire de votre dossier ?',
        'cta_body': 'Décrivez la situation et indiquez les documents disponibles. Ne transmettez pas de documents '
                    'confidentiels dans le chat public.',
        'cta_button': 'Ouvrir le formulaire',
        'fine': 'Information générale, pas un conseil juridique. Vérifiez les règles et délais actuels de la '
                'plateforme.',
        'updated': 'Mis à jour le 24 juillet 2026',
        'related': 'Guides associés',
        'home': 'Accueil'},
 'de': {'all_guides': 'Alle Ratgeber',
        'common_mistakes': 'Häufige Fehler',
        'cta_title': 'Benötigen Sie eine vorläufige Einschätzung Ihres Falls?',
        'cta_body': 'Beschreiben Sie die Situation und nennen Sie die vorhandenen Unterlagen. Senden Sie keine '
                    'vertraulichen Dokumente im öffentlichen Chat.',
        'cta_button': 'Antragsformular öffnen',
        'fine': 'Allgemeine Information, keine Rechtsberatung. Prüfen Sie aktuelle Plattformregeln und Fristen.',
        'updated': 'Aktualisiert am 24. Juli 2026',
        'related': 'Weitere Ratgeber',
        'home': 'Startseite'},
 'es': {'all_guides': 'Todas las guías',
        'common_mistakes': 'Errores frecuentes',
        'cta_title': '¿Necesita una evaluación preliminar de su caso?',
        'cta_body': 'Describa la situación e indique qué documentos tiene. No envíe documentos confidenciales en el '
                    'chat público.',
        'cta_button': 'Abrir el formulario',
        'fine': 'Información general, no asesoramiento jurídico. Compruebe las reglas y los plazos actuales de la '
                'plataforma.',
        'updated': 'Actualizado el 24 de julio de 2026',
        'related': 'Guías relacionadas',
        'home': 'Inicio'},
 'sr': {'all_guides': 'Svi vodiči',
        'common_mistakes': 'Česte greške',
        'cta_title': 'Potrebna vam je preliminarna procena slučaja?',
        'cta_body': 'Opišite situaciju i navedite dokumenta koja već imate. Ne šaljite poverljiva dokumenta kroz javni '
                    'čet.',
        'cta_button': 'Otvori prijavni obrazac',
        'fine': 'Opšte informacije, ne pravni savet. Proverite aktuelna pravila platforme i rokove.',
        'updated': 'Ažurirano 24. jula 2026.',
        'related': 'Povezani vodiči',
        'home': 'Početna'}}


GUIDE_HUB_ACCESSIBILITY = {
    "en": "Language",
    "ru": "Язык",
    "fr": "Langue",
    "de": "Sprache",
    "es": "Idioma",
    "sr": "Jezik",
}
for _language, _label in GUIDE_HUB_ACCESSIBILITY.items():
    GUIDE_HUB_COPY[_language]["language_label"] = _label

GUIDE_DETAIL_ACCESSIBILITY = {
    "en": {"language_label": "Language", "breadcrumb_label": "Breadcrumb"},
    "ru": {"language_label": "Язык", "breadcrumb_label": "Навигационная цепочка"},
    "fr": {"language_label": "Langue", "breadcrumb_label": "Fil d’Ariane"},
    "de": {"language_label": "Sprache", "breadcrumb_label": "Brotkrümelnavigation"},
    "es": {"language_label": "Idioma", "breadcrumb_label": "Ruta de navegación"},
    "sr": {"language_label": "Jezik", "breadcrumb_label": "Navigaciona putanja"},
}
for _language, _labels in GUIDE_DETAIL_ACCESSIBILITY.items():
    GUIDE_DETAIL_COPY[_language].update(_labels)

GUIDE_PUBLISHED_DATE = "2026-07-24"
GUIDE_MODIFIED_DATE = "2026-07-24"
