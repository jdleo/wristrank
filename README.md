# WristRank

The blind watch ranking game. Two watches enter, you pick a winner - brand, model and price are only revealed **after** you vote. Every result feeds a personal Elo leaderboard, and the watches you love collect into your own watch list.

**Live:** deployed on Vercel (see the project for the current URL).

## How it plays

- **Blind duels** - two watch photos, zero labels. Tap the one you'd rather wear.
- **The reveal** - brand, model, reference, market price, price tier, and the Elo swing.
- **True Elo** (start 1500, K = 32) - beating a higher-rated watch pays out more. When a cheaper-tier watch takes down a grail, that's an **upset**, and the points prove it.
- **5 price tiers** - T1 under $500 · T2 $500-2K · T3 $2K-6K · T4 $6K-15K · T5 grail $15K+. Matchmaking mostly pairs neighbours, with regular cross-tier chaos rounds.
- **My List** - bookmark any revealed watch; the list totals what your taste would cost.
- Men's watches only. Rankings persist in your browser (localStorage).

## The data (nothing hand-typed)

The catalog of 138 watches is generated once by `scripts/build_catalog.py` and cached in `data/watches.json` + `public/watches/`:

- **Prices** - median secondary-market prices computed from a 284,491-listing Chrono24 dataset (Kaggle: `philmorekoung11/luxury-watch-listings`, mirrored on Hugging Face as `yotam22/watches`). Family medians use thousands of real listings per model line (e.g. Submariner Date = median of 5,088 listings). Long-tail entries use family medians, falling back to brand medians - the per-watch `source` field says which.
- **Marquee photos** - dealer/listing photos located per reference via image search (EveryWatch, Watchfinder, Watch Club, official brand shots where available), downloaded once and verified.
- **Long-tail photos** - the Chrono24 photo archive on Hugging Face (`noxneural/watches_chrono24`, ~11,900 watches with photos), filtered to men's core-watch brands.

Rebuild the catalog with:

```sh
python3 scripts/build_catalog.py   # writes data/watches.json + public/watches/*.jpg
```

## Run it

```sh
npm install
npm run dev     # http://localhost:3000
npm run build   # production build (Next.js)
```

Built with Next.js + React, no backend - the whole game state lives client-side.
