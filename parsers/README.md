#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YouTube Parser - README

Ushbu parser YouTube videolarini tahlil qiladi va kommentariyalarni oladi.

## O'RNATISH

```bash
pip install -r requirements.txt
```

## FOYDALANISH

### 1. BIR VIDEONI TAHLIL QILISH

```bash
python main.py https://www.youtube.com/watch?v=VIDEO_ID
```

Yoki Shorts uchun:

```bash
python main.py https://www.youtube.com/shorts/VIDEO_ID
```

Kommentariyalarning sonini cheklashtirish:

```bash
python main.py https://www.youtube.com/watch?v=VIDEO_ID 500
```

### 2. FAYL DAN TAHLIL QILISH

`urls.txt` faylga video URL'larini qo'shing (har bir qatorga bitta):

```
https://www.youtube.com/watch?v=VIDEO_ID_1
https://www.youtube.com/watch?v=VIDEO_ID_2
https://www.youtube.com/shorts/SHORTS_ID
```

Keyin:

```bash
python main.py
```

## NATIJALAR

Barcha natijalar `results/` papkasiga saqlanadi:

- `video_ID_DD.MM.YYYY-HH.MM.SS.txt` - tafsil bilan bajarilgan tahlil
- `shorts_ID_DD.MM.YYYY-HH.MM.SS.txt` - Shorts uchun tahlil

## SOZLAMALAR

`settings.py` faylida quyidagi parametrlarni o'zgartirishingiz mumkin:

- `API_KEY` - YouTube API kaliti
- `MAX_RESULTS` - maksimal kommentariya soni (0 = barcha)
- `SORT_ORDER` - saralash tartibi (relevance, time, rating)
- `REQUEST_DELAY` - API so'rovlari orasidagi kecikish
- `COLLECT_REPLIES` - javoblarni saqlanishini (True/False)

## XATOLIKLAR VA MUHIM NUQTALAR

1. **API Kaliti xato** - `settings.py` da to'g'ri API kalitini kiriting
2. **Kommentariyalar yoq** - Ba'zi videolarda kommentariyalar o'chirilgan bo'lishi mumkin
3. **Rate Limiting** - YouTube API kuniga 10,000 so'rov cheklagiga ega
4. **Shorts qo'llab-quvvatlash** - 60 sekunddan qisqa videolar avtomatik "Shorts" sifatida aniqlanadi

## FAYL TUZILISHI

```
parsers/
├── main.py                 # Asosiy parser
├── youtube_api.py          # YouTube API kliyenti
├── data_models.py          # Ma'lumot modellari
├── utils.py                # Utility funksiyalari
├── settings.py             # Konfiguratsiya
├── requirements.txt        # Python dependensiyalari
├── urls.txt                # URL'lar ro'yxati
└── results/                # Tahlil natijalari
```

## LITSENZIYA

MIT License
