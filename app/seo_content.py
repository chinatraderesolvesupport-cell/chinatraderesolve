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

# Full multilingual guide content and shared detail-page labels (v3.7.36).
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


# Search-intent expansion for v3.7.49. These pages are deliberately published first
# in Russian and English, where the editorial review is complete. Other language
# alternatives are added only after a real translation exists; no fake hreflang pages.
SEO_EXPANSION_GUIDES = {
    "en": {
        "supplier-not-refunding": {
            "title": "Chinese supplier refuses to refund: what to do next",
            "description": "A practical evidence and escalation checklist when a Chinese supplier or Alibaba seller refuses to return a deposit or payment.",
            "intro": "A refund promise is not the same as a completed refund. Preserve the payment trail, the agreed cancellation or defect basis, and every deadline before deciding what to do next.",
            "summary": "Keep the claim narrow: what was paid, why the refund is due, what the seller promised, what has actually been returned, and which deadline is still open.",
            "sections": [
                ("Confirm the refund basis", ["Identify the exact reason: non-shipment, cancellation accepted in writing, defective goods, wrong specification, shortage, or another documented breach.", "Save the order terms and the message in which the supplier accepted cancellation, acknowledged the problem, or promised a refund."]),
                ("Trace the money", ["Keep the payment confirmation, beneficiary details, platform transaction record, refund status and bank statement showing that no credit arrived.", "For a partial refund, state the original payment, the amount already received and the exact balance still outstanding."]),
                ("Use one written deadline", ["Send a concise demand with the order number, amount, reason, evidence list, requested payment method and a reasonable response date.", "Do not replace a platform claim with endless private promises. Preserve any open dispute, card, bank or insurance deadline."]),
                ("Prepare the next route", ["Depending on the payment method and contract, possible routes may include the platform process, payment-provider dispute, bank inquiry, insurer, formal demand, mediation, arbitration or court.", "Do not state fraud as a fact unless the evidence supports it; describe the verifiable conduct instead."]),
            ],
            "mistakes": ["Closing a dispute before the refund reaches the account", "Sending extra money to unlock a promised refund", "Using different refund amounts in different messages", "Waiting until payment-provider or platform deadlines expire"],
            "faq": [
                ("Is a screenshot of the seller promising a refund enough?", "It helps, but combine it with the order, payment record, reason for cancellation or refund, and a bank or platform record showing that the money did not arrive."),
                ("Should I keep negotiating privately?", "Only while it does not endanger a platform, bank, card or contractual deadline. Keep private negotiations short and in writing."),
                ("Can ChinaTradeResolve guarantee recovery?", "No. The service can help organize the facts and evidence, but it cannot promise a refund or replace a lawyer or authority."),
            ],
            "related_slugs": ["alibaba-dispute-closed-no-refund", "supplier-disappeared-after-payment", "alibaba-dispute-evidence", "organize-dispute-documents"],
        },
        "supplier-disappeared-after-payment": {
            "title": "Chinese supplier disappeared after payment: evidence and first steps",
            "description": "What to preserve and check when a Chinese supplier stops replying after a deposit or full payment.",
            "intro": "Silence after payment can have several explanations, but the immediate task is the same: preserve the transaction, identity and communication evidence before accounts or pages change.",
            "summary": "Record who received the money, what was promised, the last confirmed production or shipment event, and every failed attempt to contact the supplier.",
            "sections": [
                ("Preserve identity and transaction records", ["Save the company name, registration information, Alibaba or marketplace profile, website, addresses, bank beneficiary and invoice.", "Export the complete chat where possible and keep message dates, names, attachments and voice-note context."]),
                ("Check whether the account changed", ["Document deleted listings, changed company names, blocked accounts, bounced email and disconnected phone numbers.", "Do not rely on screenshots alone when an export, PDF order or bank document is available."]),
                ("Contact through controlled channels", ["Send one clear written notice through the platform and the contractual contact address, asking for a status update or refund by a stated date.", "Avoid threats and repeated emotional messages; they make the timeline harder to review."]),
                ("Protect remaining deadlines", ["Check marketplace, Trade Assurance, card, bank-transfer, insurance and contract deadlines immediately.", "A supplier's request to wait does not automatically extend a third party's filing deadline."]),
            ],
            "mistakes": ["Paying a new fee to release goods or a refund without verification", "Deleting the chat after taking a few screenshots", "Contacting unrelated people with public accusations", "Waiting weeks before checking dispute deadlines"],
            "faq": [
                ("Does silence prove fraud?", "No. It is evidence of non-response, not automatically proof of intent. Describe the facts precisely and preserve the payment and promise records."),
                ("What is the most important document?", "Usually the combination of the order or invoice, payment proof, supplier identity and messages showing what should have happened after payment."),
                ("Should I publish the supplier's details online?", "Public accusations can create legal and practical risks. Start with controlled evidence preservation and formal channels."),
            ],
            "related_slugs": ["supplier-not-refunding", "supplier-not-shipped", "organize-dispute-documents", "alibaba-dispute-evidence"],
        },
        "damaged-or-short-shipment": {
            "title": "Damaged or missing goods from China: how to document a claim",
            "description": "Evidence checklist for damaged cartons, broken goods, missing units, short shipment or incomplete delivery from a Chinese supplier.",
            "intro": "Damage and shortage cases depend heavily on evidence created at receipt. Photograph the unopened condition, count method, labels and carrier records before repacking or distributing the goods.",
            "summary": "Show the agreed quantity, the delivered quantity, the condition at receipt, the inspection method and the financial effect of the shortage or damage.",
            "sections": [
                ("Document the arrival condition", ["Photograph the container, pallet or cartons before opening, including seals, labels, dents, moisture and visible damage.", "Keep delivery receipts and note any reservation or damage remark made to the carrier."]),
                ("Count and sample systematically", ["Use a written count sheet and identify carton numbers, SKU, batch and the person who performed the check.", "For damage, state how many units were inspected, how many failed and how the sample was selected."]),
                ("Separate carrier and supplier issues", ["Compare packaging obligations, Incoterms, transport documents and the point at which risk passed under the agreement.", "Do not assume every transport loss is the supplier's responsibility or every packaging defect is the carrier's responsibility."]),
                ("Calculate a supported remedy", ["Connect each missing or damaged unit to the invoice price and any documented inspection, disposal or repair cost.", "Preserve the goods and packaging until the relevant parties confirm whether inspection is required."]),
            ],
            "mistakes": ["Signing a clean delivery receipt despite obvious damage", "Discarding packaging before inspection", "Claiming the whole order is defective after checking only one unit", "Using an unexplained lump-sum refund demand"],
            "faq": [
                ("Should I open every carton?", "Use a defensible inspection plan and record what was checked. The correct scope depends on the shipment and dispute route."),
                ("Who is responsible for transit damage?", "That depends on the contract, Incoterms, carrier documents, packaging obligations and the actual cause. Preserve evidence before deciding."),
                ("Can a warehouse report help?", "Yes, especially when it records receipt time, seal condition, carton count, photographs and the inspection method."),
            ],
            "related_slugs": ["product-quality-dispute", "wrong-material-size-color", "alibaba-dispute-evidence", "organize-dispute-documents"],
        },
        "wrong-material-size-color": {
            "title": "Supplier sent the wrong material, size or colour: how to prove it",
            "description": "How to compare the approved specification, sample and delivered goods when material, dimensions, colour or model do not match.",
            "intro": "A wrong-specification claim is strongest when the final approved requirement can be identified and the difference can be measured or independently verified.",
            "summary": "Put the promise and the observed result side by side: final specification, approval date, test or measurement, affected quantity and requested remedy.",
            "sections": [
                ("Identify the final approved version", ["Save the final purchase order, drawings, colour code, material description, sample approval and any later revision.", "Resolve contradictions between an early chat message and the final signed or platform specification."]),
                ("Measure the mismatch", ["Use calibrated tools, colour references, labels, laboratory or expert testing where the issue cannot be established visually.", "Record the method, date, sample identity and chain of custody for any external test."]),
                ("Show commercial relevance", ["Explain why the difference affects use, compliance, resale, safety, compatibility or the agreed customer order.", "Avoid claiming that a difference is material if it has no documented effect on the transaction."]),
                ("Choose a proportional remedy", ["State whether the mismatch justifies replacement, rework, price reduction, partial refund, rejection or cancellation under the applicable terms.", "Calculate the amount from the affected quantity and supported costs rather than a round estimate."]),
            ],
            "mistakes": ["Relying on screen colour to prove a colour-code mismatch", "Calling a material fake without testing or reliable documentation", "Ignoring a later approved specification change", "Failing to identify how many units are affected"],
            "faq": [
                ("Are photographs enough to prove the wrong material?", "Sometimes not. Material composition often requires labels, supplier admissions, technical documents or independent testing."),
                ("What if the sample and purchase order conflict?", "Preserve both and identify which document was accepted as final. The sequence of approvals is important."),
                ("Should I test every unit?", "Not always, but the sample must be representative and the method should be recorded."),
            ],
            "related_slugs": ["product-quality-dispute", "damaged-or-short-shipment", "supplier-certificate-problem", "alibaba-dispute-evidence"],
        },
        "alibaba-dispute-closed-no-refund": {
            "title": "Alibaba closed the dispute without a refund: what to review",
            "description": "A structured checklist for reviewing an Alibaba dispute decision, missed evidence, deadlines and possible next escalation routes.",
            "intro": "A closed platform dispute does not by itself explain whether the evidence was insufficient, the claim was inconsistent, a deadline was missed or the decision can still be reviewed through another route.",
            "summary": "Preserve the complete case file, identify the exact decision and rule cited, then compare the evidence submitted with the issue and remedy you asked Alibaba to decide.",
            "sections": [
                ("Save the complete dispute record", ["Download or capture the claim, seller response, platform questions, evidence list, status changes, decision and closure date.", "Keep the order page and the version of Trade Assurance or other terms that applied to the transaction."]),
                ("Read the stated reason", ["Separate a procedural closure, deadline issue, insufficient evidence finding and substantive rejection.", "Do not assume the decision addressed a point that was never clearly raised or documented."]),
                ("Audit your own submission", ["Check whether dates, amounts, requested remedy and main issue stayed consistent across all dispute rounds.", "Match each important statement to a specific file and note evidence that Alibaba requested but did not receive or discuss."]),
                ("Map remaining options", ["Check whether review, appeal, complaint, payment-provider, insurer, formal demand, mediation, arbitration or court routes remain available.", "Deadlines and jurisdiction depend on the contract, entity, payment route and location; do not rely on a generic internet deadline."]),
            ],
            "mistakes": ["Deleting the closed-case pages", "Starting a new complaint with a different unsupported story", "Assuming a platform decision is the same as a court judgment", "Missing external payment or contractual deadlines while waiting for support"],
            "faq": [
                ("Can a closed Alibaba dispute be reopened?", "That depends on the case status, current platform procedure and available new evidence. Preserve the record and check the current options shown in the account."),
                ("Does closure mean the supplier was proven right?", "Not necessarily. A case may close for procedural or evidentiary reasons. Read the exact wording and history."),
                ("What should a review request contain?", "A concise chronology, the exact error alleged, the evidence that supports it and a specific requested outcome."),
            ],
            "related_slugs": ["alibaba-dispute-evidence", "supplier-not-refunding", "organize-dispute-documents", "product-quality-dispute"],
        },
        "supplier-certificate-problem": {
            "title": "Wrong or invalid certificate from a Chinese supplier: what to check",
            "description": "Evidence checklist when a certificate is missing, unrelated to the goods, unverifiable, expired or unsuitable for the destination market.",
            "intro": "A logo or PDF labelled 'certificate' is not enough. The key questions are what document was promised, who issued it, which product and standard it covers, and whether it is valid for the intended market.",
            "summary": "Compare the promised compliance document with the actual issuer, certificate number, product model, standard, scope, dates and destination requirements.",
            "sections": [
                ("Preserve what was promised", ["Save the messages, quotation and order term stating which certificate, test report, declaration or registration the supplier would provide.", "Record whether the document was a condition of payment, production approval, shipment or import."]),
                ("Verify the document", ["Check issuer contact details, certificate number, product model, applicant, manufacturer, standard, issue and expiry dates and any online database.", "Contact the stated issuer through independently obtained contact information when verification matters."]),
                ("Distinguish document types", ["A test report, certificate, declaration of conformity, factory audit and product registration are not interchangeable.", "Do not describe a document as forged unless there is reliable evidence; state the precise inconsistency or failed verification."]),
                ("Connect it to the transaction", ["Explain why the missing or unsuitable document prevents lawful import, sale, installation or the agreed use.", "Preserve customs, laboratory, consultant or authority correspondence that identifies the problem."]),
            ],
            "mistakes": ["Accepting a certificate for a different model or manufacturer", "Relying only on a supplier-provided verification link", "Confusing a test report with market authorization", "Making a forgery allegation before verification"],
            "faq": [
                ("How can I verify a certificate?", "Check the issuer independently, the certificate number, scope, model and dates. Requirements differ by product and destination."),
                ("Is a CE logo proof of compliance?", "No. A mark alone does not establish that all applicable conformity obligations and documentation are satisfied."),
                ("Can this support cancellation or refund?", "Possibly, when the document was an agreed condition or the goods cannot lawfully be used as intended. The contract and evidence matter."),
            ],
            "related_slugs": ["customs-clearance-problem", "wrong-material-size-color", "alibaba-dispute-evidence", "organize-dispute-documents"],
        },
        "customs-clearance-problem": {
            "title": "Goods from China are stuck at customs: supplier-dispute checklist",
            "description": "How to organize evidence when Chinese goods are delayed or rejected by customs because of invoices, classification, certificates or markings.",
            "intro": "A customs problem is not automatically a supplier breach. First identify the official reason, the importer of record, the agreed Incoterm and which party promised each document or compliance step.",
            "summary": "Start with the written customs notice, then map each missing or incorrect item to the contract, shipping documents and responsible party.",
            "sections": [
                ("Obtain the official reason", ["Request the customs, broker, carrier or authority notice that states what is missing, inconsistent, prohibited or under review.", "Separate an ordinary document request from detention, seizure, rejection, return or destruction risk."]),
                ("Map responsibilities", ["Check the Incoterm, importer of record, customs-broker instruction and contractual promises about classification, origin, value, certificates and markings.", "Do not assume 'door to door' transfers every legal obligation without reading the written agreement."]),
                ("Preserve the document chain", ["Save the commercial invoice, packing list, bill of lading or airway bill, HS code, origin documents, certificates, declarations and supplier instructions.", "Record each corrected document and who issued it to avoid losing the audit trail."]),
                ("Control costs and deadlines", ["Track storage, demurrage, broker, testing, return and destruction deadlines with supporting invoices or notices.", "Before paying a new supplier-requested fee, verify the recipient and obtain a written explanation of what the payment resolves."]),
            ],
            "mistakes": ["Relying only on the supplier's summary of the customs issue", "Changing invoices without preserving the original", "Ignoring storage or abandonment deadlines", "Assuming the supplier is responsible without checking the Incoterm and importer role"],
            "faq": [
                ("Who is responsible when customs stops the goods?", "It depends on the official reason, import law, importer role, Incoterm and contractual promises. The customs notice is the starting point."),
                ("Should the supplier issue a new invoice?", "Only when a genuine error needs correction. Preserve the original and do not use false values or descriptions."),
                ("Can customs costs be claimed from the supplier?", "Potentially, if a documented supplier breach caused them and the contract or applicable law supports recovery. Keep every cost record."),
            ],
            "related_slugs": ["supplier-certificate-problem", "order-not-delivered-tracking-problem", "supplier-not-shipped", "organize-dispute-documents"],
        },
        "order-not-delivered-tracking-problem": {
            "title": "Order from China not delivered: tracking and evidence checklist",
            "description": "What to collect when tracking is invalid, frozen, delivered to the wrong place or shows delivery that you did not receive.",
            "intro": "Non-delivery after dispatch is different from non-shipment. Build a carrier-level timeline and identify the route, consignee, delivery scan and any exception or proof-of-delivery document.",
            "summary": "Preserve the agreed destination, carrier record, tracking history, delivery evidence, communications and the point at which the shipment stopped or was misdelivered.",
            "sections": [
                ("Capture the tracking history", ["Save the carrier name, full tracking number and dated scan history rather than only the latest status.", "Verify the number on the carrier's official system and record any mismatch in destination, weight or service."]),
                ("Request proof of delivery", ["Ask for the delivery address, recipient name, signature, photograph, GPS or local carrier record where available.", "A generic 'delivered' status may not show that the correct consignee received the goods."]),
                ("Trace handovers", ["Identify freight forwarders, consolidators, customs brokers and last-mile carriers, including every replacement tracking number.", "Record when risk and responsibility passed under the contract and Incoterm."]),
                ("Notify the right parties", ["Send timely written notice to the seller, platform, carrier, insurer and payment provider where applicable.", "Keep claim reference numbers and do not discard packaging or delivery documents for partial shipments."]),
            ],
            "mistakes": ["Using a tracking screenshot without the carrier name", "Waiting until the carrier claim period expires", "Confusing a warehouse delivery with delivery to the buyer", "Failing to record replacement tracking numbers"],
            "faq": [
                ("What if tracking says delivered but nothing arrived?", "Request detailed proof of delivery and compare the address, recipient, weight and local carrier record with the order."),
                ("Is the seller always responsible for lost transit?", "Not always. Contract terms, Incoterms, insurance and the point of loss matter."),
                ("What if the tracking number is fake?", "Document the official carrier response, inconsistencies and supplier messages. Avoid conclusions beyond the evidence."),
            ],
            "related_slugs": ["supplier-not-shipped", "customs-clearance-problem", "damaged-or-short-shipment", "alibaba-dispute-evidence"],
        },
    },
    "ru": {
        "supplier-not-refunding": {
            "title": "Китайский поставщик не возвращает деньги: что делать",
            "description": "Пошаговая проверка доказательств и вариантов действий, если поставщик из Китая или продавец Alibaba не возвращает предоплату или оплату.",
            "intro": "Обещание вернуть деньги ещё не означает, что возврат состоялся. Сохраните платёжный след, основание возврата, переписку и все действующие сроки.",
            "summary": "Сведите дело к пяти вопросам: сколько оплачено, почему деньги должны быть возвращены, что признал продавец, сколько фактически вернулось и какой срок ещё не пропущен.",
            "sections": [
                ("Определите основание возврата", ["Укажите конкретную причину: товар не отправлен, отмена согласована, товар бракованный, спецификация нарушена, есть недостача или другое подтверждённое нарушение.", "Сохраните условия заказа и сообщение, где продавец согласился на отмену, признал проблему или пообещал возврат."]),
                ("Проследите движение денег", ["Сохраните подтверждение оплаты, данные получателя, запись операции на платформе, статус возврата и выписку, показывающую, что деньги не поступили.", "При частичном возврате отдельно укажите первоначальную сумму, уже полученную часть и точный остаток."]),
                ("Установите один письменный срок", ["Направьте краткое требование с номером заказа, суммой, основанием, перечнем доказательств, способом возврата и датой ответа.", "Не заменяйте действующий спор бесконечными обещаниями в личной переписке и не пропускайте сроки банка, карты, страховщика или платформы."]),
                ("Подготовьте следующий маршрут", ["В зависимости от договора и способа оплаты возможны процедура платформы, спор по платежу, обращение в банк, к страховщику, официальная претензия, медиация, арбитраж или суд.", "Не называйте действия мошенничеством без достаточных доказательств — описывайте проверяемые факты."]),
            ],
            "mistakes": ["Закрыть спор до фактического поступления денег", "Перевести дополнительную сумму ради обещанного возврата", "Указывать разные суммы требования в разных сообщениях", "Дождаться истечения сроков платформы или платёжного сервиса"],
            "faq": [
                ("Достаточно ли скриншота, где продавец обещает возврат?", "Он полезен, но его нужно соединить с заказом, оплатой, основанием отмены или возврата и доказательством того, что деньги не поступили."),
                ("Стоит ли продолжать личные переговоры?", "Только пока они не угрожают срокам платформы, банка, карты или договора. Переговоры должны быть короткими и письменными."),
                ("Гарантирует ли ChinaTradeResolve возврат?", "Нет. Сервис помогает организовать факты и доказательства, но не обещает возврат и не заменяет адвоката или государственный орган."),
            ],
            "related_slugs": ["alibaba-dispute-closed-no-refund", "supplier-disappeared-after-payment", "alibaba-dispute-evidence", "organize-dispute-documents"],
        },
        "supplier-disappeared-after-payment": {
            "title": "Китайский поставщик пропал после оплаты: что сохранить и проверить",
            "description": "Какие доказательства собрать и какие сроки проверить, если поставщик из Китая перестал отвечать после предоплаты или полной оплаты.",
            "intro": "Молчание после оплаты может иметь разные причины, но первая задача одна: зафиксировать платёж, личность получателя, обещания и переписку до изменения аккаунтов и страниц.",
            "summary": "Зафиксируйте, кому ушли деньги, что было обещано, какое событие производства или отправки подтверждено последним и когда продавец перестал отвечать.",
            "sections": [
                ("Сохраните данные поставщика и сделки", ["Скачайте название компании, регистрационные сведения, профиль Alibaba или другой площадки, сайт, адреса, банковского получателя и инвойс.", "Экспортируйте полный чат, сохранив даты, имена, вложения и контекст голосовых сообщений."]),
                ("Проверьте изменения аккаунта", ["Зафиксируйте удалённые объявления, смену названия компании, блокировку аккаунта, недоставленные письма и отключённые телефоны.", "Не ограничивайтесь скриншотами, когда доступен экспорт переписки, PDF заказа или банковский документ."]),
                ("Свяжитесь через контролируемые каналы", ["Отправьте одно понятное уведомление через платформу и договорной адрес с просьбой дать статус или вернуть деньги к конкретной дате.", "Избегайте угроз и десятков эмоциональных сообщений — они затрудняют анализ хронологии."]),
                ("Защитите оставшиеся сроки", ["Сразу проверьте сроки площадки, Trade Assurance, банка, карты, страховки и договора.", "Просьба продавца подождать не продлевает автоматически срок обращения к третьей стороне."]),
            ],
            "mistakes": ["Оплатить новый сбор за разблокировку товара или возврата без проверки", "Удалить чат после нескольких скриншотов", "Публично обвинять непричастных лиц", "Неделями не проверять сроки открытия спора"],
            "faq": [
                ("Доказывает ли молчание мошенничество?", "Нет. Оно подтверждает отсутствие ответа, но не доказывает умысел. Точно описывайте факты и сохраняйте платёж и обещания."),
                ("Какой документ самый важный?", "Обычно важна связка: заказ или инвойс, подтверждение оплаты, данные поставщика и сообщения о том, что должно было произойти после платежа."),
                ("Нужно ли публиковать данные поставщика в интернете?", "Публичные обвинения могут создать правовые и практические риски. Сначала сохраните доказательства и используйте официальные каналы."),
            ],
            "related_slugs": ["supplier-not-refunding", "supplier-not-shipped", "organize-dispute-documents", "alibaba-dispute-evidence"],
        },
        "damaged-or-short-shipment": {
            "title": "Из Китая пришёл повреждённый товар или недостача: как доказать",
            "description": "Памятка по доказательствам при повреждении коробок и товара, нехватке единиц, неполной комплектации или недостаче в поставке из Китая.",
            "intro": "В спорах о повреждении и недостаче особенно важны доказательства, созданные в момент получения. Снимите закрытую упаковку, пломбы, маркировку и процедуру подсчёта до переупаковки товара.",
            "summary": "Покажите согласованное количество, фактически полученное количество, состояние при приёмке, метод проверки и финансовые последствия недостачи или повреждения.",
            "sections": [
                ("Зафиксируйте состояние при получении", ["Снимите контейнер, паллету или коробки до вскрытия: пломбы, этикетки, вмятины, влагу и видимые повреждения.", "Сохраните накладные и внесите оговорку о повреждении в документ перевозчика, когда это возможно."]),
                ("Проведите понятный подсчёт", ["Используйте письменный лист подсчёта с номерами коробок, артикулами, партиями и именем проверяющего.", "Для брака укажите, сколько единиц проверено, сколько не прошло проверку и как выбиралась выборка."]),
                ("Разделите ответственность перевозчика и поставщика", ["Сопоставьте требования к упаковке, Incoterms, транспортные документы и момент перехода риска.", "Не считайте автоматически любой транспортный ущерб ответственностью продавца, а любую плохую упаковку — ответственностью перевозчика."]),
                ("Рассчитайте подтверждённое требование", ["Свяжите каждую недостающую или повреждённую единицу с ценой в инвойсе и подтверждёнными расходами на проверку, ремонт или утилизацию.", "Сохраните товар и упаковку до решения вопроса о необходимости осмотра."]),
            ],
            "mistakes": ["Подписать чистую накладную при заметном повреждении", "Выбросить упаковку до осмотра", "Заявить брак всей партии после проверки одной единицы", "Потребовать круглую сумму без расчёта"],
            "faq": [
                ("Нужно ли вскрывать все коробки?", "Используйте обоснованный план проверки и записывайте, что именно осмотрено. Масштаб зависит от партии и процедуры спора."),
                ("Кто отвечает за повреждение в пути?", "Это зависит от договора, Incoterms, документов перевозчика, упаковочных обязанностей и фактической причины."),
                ("Поможет ли акт склада?", "Да, особенно если в нём указаны время приёмки, состояние пломб, количество мест, фотографии и метод проверки."),
            ],
            "related_slugs": ["product-quality-dispute", "wrong-material-size-color", "alibaba-dispute-evidence", "organize-dispute-documents"],
        },
        "wrong-material-size-color": {
            "title": "Поставщик прислал другой материал, размер или цвет: как доказать",
            "description": "Как сравнить утверждённую спецификацию, образец и поставленный товар, если не совпадают материал, размеры, цвет или модель.",
            "intro": "Претензия по неверной спецификации сильнее, когда можно определить окончательно согласованное требование и измерить или независимо подтвердить отличие.",
            "summary": "Поставьте рядом обещание и результат: окончательная спецификация, дата утверждения, измерение или тест, количество затронутого товара и требование.",
            "sections": [
                ("Найдите окончательно утверждённую версию", ["Сохраните финальный заказ, чертежи, код цвета, описание материала, утверждение образца и последующие изменения.", "Разрешите противоречия между ранней перепиской и окончательной спецификацией на платформе или в подписанном документе."]),
                ("Измерьте несоответствие", ["Используйте поверенные инструменты, цветовые эталоны, маркировку, лабораторный или экспертный тест, когда визуального сравнения недостаточно.", "Для внешнего теста запишите метод, дату, идентификацию образца и цепочку хранения."]),
                ("Покажите коммерческое значение", ["Объясните, почему отличие влияет на применение, соответствие требованиям, перепродажу, безопасность, совместимость или заказ клиента.", "Не называйте отличие существенным, если его влияние на сделку ничем не подтверждено."]),
                ("Выберите соразмерное требование", ["Укажите, требует ли отличие замены, переделки, снижения цены, частичного возврата, отказа от товара или отмены по условиям сделки.", "Рассчитайте сумму от количества затронутых единиц и подтверждённых затрат."]),
            ],
            "mistakes": ["Доказывать оттенок только по цвету экрана", "Называть материал поддельным без теста или надёжных документов", "Игнорировать позднее согласованное изменение", "Не указывать количество затронутых единиц"],
            "faq": [
                ("Достаточно ли фотографий для доказательства другого материала?", "Не всегда. Состав материала часто требует маркировки, признания продавца, технических документов или независимого теста."),
                ("Что делать, если образец и заказ противоречат друг другу?", "Сохраните оба источника и установите, какой из них был принят как окончательный. Последовательность согласований имеет значение."),
                ("Нужно ли тестировать каждую единицу?", "Не всегда, но выборка должна быть репрезентативной, а метод проверки — записан."),
            ],
            "related_slugs": ["product-quality-dispute", "damaged-or-short-shipment", "supplier-certificate-problem", "alibaba-dispute-evidence"],
        },
        "alibaba-dispute-closed-no-refund": {
            "title": "Alibaba закрыла спор без возврата денег: что проверить",
            "description": "Структурированная проверка решения Alibaba, представленных доказательств, сроков и возможных дальнейших маршрутов.",
            "intro": "Закрытие спора не показывает само по себе, было ли недостаточно доказательств, пропущен срок, требование сформулировано непоследовательно или остаётся другой путь пересмотра.",
            "summary": "Сохраните полное дело, найдите точную причину решения и сопоставьте поданные доказательства с вопросом и требованием, которые вы просили Alibaba рассмотреть.",
            "sections": [
                ("Сохраните полную историю спора", ["Скачайте или снимите заявление, ответ продавца, вопросы платформы, перечень доказательств, изменения статуса, решение и дату закрытия.", "Сохраните страницу заказа и редакцию Trade Assurance или других условий, действовавших для сделки."]),
                ("Прочитайте указанную причину", ["Отделите процедурное закрытие, пропуск срока, недостаточность доказательств и отказ по существу.", "Не предполагайте, что решение рассмотрело вопрос, который не был ясно заявлен и подтверждён."]),
                ("Проведите аудит своей подачи", ["Проверьте, совпадали ли даты, суммы, требование и главная проблема во всех этапах спора.", "Свяжите каждое важное утверждение с конкретным файлом и отметьте доказательства, которые Alibaba запрашивала, но не получила или не обсудила."]),
                ("Определите оставшиеся варианты", ["Проверьте возможность пересмотра, жалобы, спора по платежу, обращения к страховщику, официальной претензии, медиации, арбитража или суда.", "Сроки и юрисдикция зависят от договора, юридического лица, платежа и места сторон — не полагайтесь на универсальный срок из интернета."]),
            ],
            "mistakes": ["Удалить страницы закрытого дела", "Начать новую жалобу с другой неподтверждённой версией", "Считать решение платформы судебным решением", "Пропустить внешние сроки, ожидая ответа поддержки"],
            "faq": [
                ("Можно ли открыть закрытый спор Alibaba заново?", "Это зависит от статуса дела, текущей процедуры платформы и новых доказательств. Сохраните дело и проверьте доступные действия в аккаунте."),
                ("Означает ли закрытие, что продавец доказал свою правоту?", "Не обязательно. Дело может быть закрыто по процедуре или из-за доказательств. Важна точная формулировка решения."),
                ("Что включить в просьбу о пересмотре?", "Краткую хронологию, точную предполагаемую ошибку, подтверждающие её доказательства и конкретный результат, которого вы просите."),
            ],
            "related_slugs": ["alibaba-dispute-evidence", "supplier-not-refunding", "organize-dispute-documents", "product-quality-dispute"],
        },
        "supplier-certificate-problem": {
            "title": "Китайский поставщик дал неправильный или недействительный сертификат",
            "description": "Что проверить, если сертификат отсутствует, относится к другому товару, не подтверждается, просрочен или не подходит для рынка назначения.",
            "intro": "Логотип или PDF с названием certificate ещё ничего не доказывает. Нужно установить, какой документ обещали, кем он выдан, какой товар и стандарт охватывает и подходит ли рынку назначения.",
            "summary": "Сопоставьте обещанный документ с фактическим органом, номером, моделью товара, стандартом, областью действия, датами и требованиями страны ввоза.",
            "sections": [
                ("Сохраните обещание продавца", ["Зафиксируйте сообщения, коммерческое предложение и условие заказа о конкретном сертификате, протоколе испытаний, декларации или регистрации.", "Укажите, был ли документ условием оплаты, запуска производства, отправки или импорта."]),
                ("Проверьте документ", ["Проверьте контакты органа, номер документа, модель, заявителя, изготовителя, стандарт, даты выдачи и окончания, а также доступную официальную базу.", "При необходимости свяжитесь с указанным органом по контактам, найденным независимо от поставщика."]),
                ("Различайте типы документов", ["Протокол испытаний, сертификат, декларация соответствия, аудит фабрики и регистрация товара не взаимозаменяемы.", "Не называйте документ поддельным без надёжного подтверждения — укажите конкретное несоответствие или неудачную проверку."]),
                ("Свяжите проблему со сделкой", ["Объясните, почему отсутствующий или неподходящий документ препятствует законному импорту, продаже, установке или согласованному применению.", "Сохраните письма таможни, лаборатории, консультанта или органа, где описана проблема."]),
            ],
            "mistakes": ["Принять сертификат на другую модель или изготовителя", "Проверять документ только по ссылке продавца", "Путать протокол испытаний с разрешением на рынок", "Обвинять в подделке до проверки"],
            "faq": [
                ("Как проверить сертификат?", "Независимо проверьте орган, номер, область действия, модель и даты. Требования различаются по товару и стране."),
                ("Доказывает ли знак CE соответствие?", "Нет. Сам знак не подтверждает выполнение всех применимых процедур и наличие правильной документации."),
                ("Может ли проблема с сертификатом быть основанием для возврата?", "Возможно, если документ был согласованным условием или товар нельзя законно использовать по назначению. Важны договор и доказательства."),
            ],
            "related_slugs": ["customs-clearance-problem", "wrong-material-size-color", "alibaba-dispute-evidence", "organize-dispute-documents"],
        },
        "customs-clearance-problem": {
            "title": "Товар из Китая застрял на таможне: что проверять в споре",
            "description": "Как собрать документы, если груз задержан или не выпускается из-за инвойса, кода товара, сертификатов, маркировки или импортных требований.",
            "intro": "Проблема на таможне не всегда означает нарушение поставщика. Сначала получите официальную причину, установите импортёра, Incoterm и письменные обязанности сторон по документам.",
            "summary": "Начните с письменного уведомления таможни, затем свяжите каждый отсутствующий или неправильный документ с договором, перевозкой и ответственной стороной.",
            "sections": [
                ("Получите официальную причину", ["Запросите уведомление таможни, брокера, перевозчика или органа, где указано, что отсутствует, противоречит, запрещено или проверяется.", "Разделите обычный запрос документа, задержание, изъятие, отказ во ввозе, возврат и риск уничтожения."]),
                ("Распределите обязанности", ["Проверьте Incoterm, импортёра, инструкции брокеру и обещания по классификации, происхождению, стоимости, сертификатам и маркировке.", "Не считайте, что формулировка door to door автоматически переносит все юридические обязанности без письменных условий."]),
                ("Сохраните цепочку документов", ["Соберите коммерческий инвойс, упаковочный лист, коносамент или авианакладную, код ТН ВЭД/HS, происхождение, сертификаты, декларации и инструкции продавца.", "Сохраняйте каждую исправленную версию и её автора, чтобы не потерять историю."]),
                ("Контролируйте расходы и сроки", ["Фиксируйте хранение, демередж, брокера, тестирование, возврат и сроки уничтожения с подтверждающими счетами и уведомлениями.", "Перед новой оплатой по просьбе поставщика проверьте получателя и письменное объяснение того, что именно решает платёж."]),
            ],
            "mistakes": ["Полагаться только на пересказ поставщика", "Менять инвойсы без сохранения оригинала", "Игнорировать сроки хранения или отказа от груза", "Назначить виновного без проверки Incoterm и роли импортёра"],
            "faq": [
                ("Кто отвечает, если таможня остановила груз?", "Это зависит от официальной причины, импортных правил, роли импортёра, Incoterm и договорных обещаний. Начинайте с уведомления таможни."),
                ("Нужно ли просить новый инвойс?", "Только для исправления реальной ошибки. Сохраните оригинал и не используйте ложную стоимость или описание."),
                ("Можно ли взыскать таможенные расходы с поставщика?", "Возможно, если их вызвало доказанное нарушение продавца и это допускают договор или применимые правила. Сохраняйте каждый расход."),
            ],
            "related_slugs": ["supplier-certificate-problem", "order-not-delivered-tracking-problem", "supplier-not-shipped", "organize-dispute-documents"],
        },
        "order-not-delivered-tracking-problem": {
            "title": "Заказ из Китая не доставлен: трекинг и доказательства",
            "description": "Что собрать, если трек-номер недействителен, не обновляется, показывает чужой адрес или доставку, которой не было.",
            "intro": "Недоставка после передачи перевозчику отличается от неотправки. Нужна хронология перевозчика, маршрут, получатель, подтверждение вручения и сведения обо всех исключениях.",
            "summary": "Сохраните согласованный адрес, перевозчика, историю трекинга, доказательство вручения, переписку и точку, где груз остановился или был доставлен не туда.",
            "sections": [
                ("Зафиксируйте полную историю трекинга", ["Сохраните перевозчика, полный номер и все датированные сканы, а не только последний статус.", "Проверьте номер на официальном сайте перевозчика и запишите различия в адресе, весе или услуге."]),
                ("Запросите доказательство вручения", ["Попросите адрес доставки, имя получателя, подпись, фотографию, GPS или запись местного перевозчика, когда они доступны.", "Общий статус delivered не доказывает, что товар получил правильный адресат."]),
                ("Проследите все передачи", ["Установите экспедиторов, консолидаторов, брокеров и последнюю милю, включая каждый новый трек-номер.", "Зафиксируйте момент перехода риска и ответственности по договору и Incoterm."]),
                ("Уведомите нужные стороны", ["Своевременно письменно уведомите продавца, платформу, перевозчика, страховщика и платёжный сервис, когда это применимо.", "Сохраняйте номера обращений и не выбрасывайте упаковку или документы частичной доставки."]),
            ],
            "mistakes": ["Показать трекинг без названия перевозчика", "Пропустить срок претензии перевозчику", "Перепутать доставку на склад посредника с доставкой покупателю", "Не сохранить сменившиеся трек-номера"],
            "faq": [
                ("Что делать, если написано «доставлено», но товара нет?", "Запросите подробное подтверждение вручения и сравните адрес, получателя, вес и запись местного перевозчика с заказом."),
                ("Всегда ли продавец отвечает за потерю в пути?", "Не всегда. Важны договор, Incoterms, страхование и место утраты."),
                ("Что делать с поддельным трек-номером?", "Сохраните официальный ответ перевозчика, несоответствия и переписку продавца. Не делайте выводов шире доказательств."),
            ],
            "related_slugs": ["supplier-not-shipped", "customs-clearance-problem", "damaged-or-short-shipment", "alibaba-dispute-evidence"],
        },
    },
}

# Make the four original pages more query-oriented without changing their evidence-based body.
GUIDES["en"]["alibaba-dispute-evidence"].update({
    "title": "What evidence is needed for an Alibaba dispute?",
    "description": "Alibaba dispute evidence checklist covering order terms, messages, payment records, inspection files, defects and a clear refund request.",
    "summary": "Build a dated chronology and connect every important statement to a specific order term, message, payment record, photograph, video or inspection file.",
    "related_slugs": ["alibaba-dispute-closed-no-refund", "supplier-not-refunding", "product-quality-dispute", "organize-dispute-documents"],
})
GUIDES["en"]["supplier-not-shipped"].update({
    "title": "Chinese supplier did not ship a paid order: what to do",
    "description": "Evidence and deadline checklist when a Chinese supplier has not shipped, falsely marked an order as shipped or missed the agreed dispatch date.",
    "summary": "Prove the agreed dispatch deadline, payment, lack of carrier handover and every extension that you did or did not accept.",
    "related_slugs": ["order-not-delivered-tracking-problem", "supplier-not-refunding", "supplier-disappeared-after-payment", "alibaba-dispute-evidence"],
})
GUIDES["en"]["product-quality-dispute"].update({
    "title": "Defective goods from China: how to prove a quality dispute",
    "description": "How to document defective goods, poor workmanship and wrong specifications by comparing the agreed standard with objective evidence.",
    "summary": "Identify the final agreed standard, document the defect objectively, state the affected quantity and connect the requested remedy to the evidence.",
    "related_slugs": ["wrong-material-size-color", "damaged-or-short-shipment", "alibaba-dispute-evidence", "organize-dispute-documents"],
})
GUIDES["en"]["organize-dispute-documents"].update({
    "title": "How to organize evidence for a Chinese supplier dispute",
    "description": "A practical folder, filename, chronology and evidence-index method for an Alibaba or Chinese-supplier dispute.",
    "summary": "Keep originals unchanged, use dated file names, create an evidence index and prepare a one-page case summary linked to source files.",
    "related_slugs": ["alibaba-dispute-evidence", "alibaba-dispute-closed-no-refund", "supplier-not-refunding", "product-quality-dispute"],
})
GUIDES["ru"]["alibaba-dispute-evidence"].update({
    "title": "Какие доказательства нужны для спора на Alibaba",
    "description": "Памятка по доказательствам для спора Alibaba: условия заказа, переписка, оплата, инспекция, брак и понятное требование о возврате.",
    "summary": "Составьте хронологию и свяжите каждое важное утверждение с конкретным условием заказа, сообщением, оплатой, фотографией, видео или актом проверки.",
    "related_slugs": ["alibaba-dispute-closed-no-refund", "supplier-not-refunding", "product-quality-dispute", "organize-dispute-documents"],
})
GUIDES["ru"]["supplier-not-shipped"].update({
    "title": "Поставщик из Китая не отправил оплаченный товар: что делать",
    "description": "Какие доказательства и сроки проверить, если поставщик из Китая не отправил заказ, поставил ложный статус отправки или сорвал согласованную дату.",
    "summary": "Докажите согласованную дату отправки, оплату, отсутствие передачи перевозчику и каждое перенесение срока, которое вы приняли или отклонили.",
    "related_slugs": ["order-not-delivered-tracking-problem", "supplier-not-refunding", "supplier-disappeared-after-payment", "alibaba-dispute-evidence"],
})
GUIDES["ru"]["product-quality-dispute"].update({
    "title": "Из Китая пришёл бракованный товар: как доказать проблему",
    "description": "Как документировать брак, плохое качество и несоответствие спецификации, сравнивая согласованный стандарт с объективными доказательствами.",
    "summary": "Установите окончательный стандарт, объективно зафиксируйте дефект, укажите количество затронутого товара и свяжите требование с доказательствами.",
    "related_slugs": ["wrong-material-size-color", "damaged-or-short-shipment", "alibaba-dispute-evidence", "organize-dispute-documents"],
})
GUIDES["ru"]["organize-dispute-documents"].update({
    "title": "Как организовать доказательства для спора с китайским поставщиком",
    "description": "Папки, названия файлов, хронология и индекс доказательств для спора на Alibaba или с поставщиком из Китая.",
    "summary": "Храните оригиналы неизменными, используйте датированные имена файлов, составьте индекс доказательств и одностраничное резюме со ссылками на источники.",
    "related_slugs": ["alibaba-dispute-evidence", "alibaba-dispute-closed-no-refund", "supplier-not-refunding", "product-quality-dispute"],
})

for _lang, _guide_map in SEO_EXPANSION_GUIDES.items():
    GUIDES[_lang].update(_guide_map)

# Rebuild cards after all guide additions and title refinements.
for _lang in SUPPORTED_LANGUAGES:
    GUIDE_CARD_COPY[_lang] = {
        _slug: {"title": _data["title"], "description": _data["description"]}
        for _slug, _data in GUIDES[_lang].items()
    }

GUIDE_DETAIL_COPY["en"].update({
    "quick_answer": "Quick answer",
    "faq": "Frequently asked questions",
    "prepared_by": "Prepared by ChinaTradeResolve Case Review Team",
    "editorial_note": "This guide explains evidence organization and practical next steps. It does not predict an outcome or replace legal advice.",
})
GUIDE_DETAIL_COPY["ru"].update({
    "quick_answer": "Короткий ответ",
    "faq": "Частые вопросы",
    "prepared_by": "Подготовлено командой разбора дел ChinaTradeResolve",
    "editorial_note": "Материал объясняет организацию доказательств и практические следующие шаги. Он не прогнозирует результат и не заменяет юридическую консультацию.",
})
for _lang in ("fr", "de", "es", "sr"):
    GUIDE_DETAIL_COPY[_lang].setdefault("quick_answer", {
        "fr": "Réponse courte", "de": "Kurzantwort", "es": "Respuesta breve", "sr": "Kratak odgovor"
    }[_lang])
    GUIDE_DETAIL_COPY[_lang].setdefault("faq", {
        "fr": "Questions fréquentes", "de": "Häufige Fragen", "es": "Preguntas frecuentes", "sr": "Česta pitanja"
    }[_lang])
    GUIDE_DETAIL_COPY[_lang].setdefault("prepared_by", {
        "fr": "Préparé par l’équipe d’examen ChinaTradeResolve",
        "de": "Erstellt vom ChinaTradeResolve-Fallprüfungsteam",
        "es": "Preparado por el equipo de revisión de ChinaTradeResolve",
        "sr": "Pripremio ChinaTradeResolve tim za pregled slučajeva",
    }[_lang])
    GUIDE_DETAIL_COPY[_lang].setdefault("editorial_note", GUIDE_DETAIL_COPY[_lang]["fine"])

GUIDE_MODIFIED_DATE = "2026-07-26"
