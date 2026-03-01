# Terminal Space Invaders

A feature-rich Space Invaders game for the terminal, built in Python using the curses library. Includes animated sprites, destructible barriers, a UFO bonus ship, alien bombs with blast radius, and a fully configurable gameplay engine.

## Features

- **Colorful ASCII art** with animated wing-flapping invaders and color cycling effects
- **5 rows x 8 columns** invader formation with three point tiers (30/20/10 pts)
- **Destructible barriers** that degrade realistically on impact
- **UFO bonus ship** that appears randomly for 50-300 bonus points
- **Alien bombs** with blast radius and explosion animations
- **Ripple effects** and visual feedback throughout
- **Level progression** with increasing difficulty (invaders start lower, move faster)
- **Lives system** with respawn delay
- **Persistent high score** tracking
- **Terminal resize handling** — adapts on the fly
- **Fully configurable** via `config.json` (speeds, sprites, colors, formation size, and more)

## Requirements

- Python 3.6+
- Terminal with color support
- Minimum terminal size: 40x20

## Installation

Clone the repo and run — no dependencies beyond the Python standard library:

```bash
git clone https://github.com/ringger/space-invaders.git
cd space-invaders
python3 space_invaders.py
```

## Controls

| Key | Action |
|-----|--------|
| **A** / **←** | Move left |
| **D** / **→** | Move right |
| **Space** | Shoot |
| **Q** | Quit |

## Configuration

All gameplay parameters are exposed in `config.json`:

| Section | What you can tweak |
|---|---|
| `display` | Minimum terminal size, color assignments |
| `player` | Lives, max bullets, respawn delay, sprite |
| `invaders.formation` | Rows, columns, spacing |
| `invaders.movement` | Speed, acceleration, step size |
| `invaders.weapons` | Bullet and bomb probability |
| `ufo` | Spawn timing, point values, sprite |
| `barriers` | Count, size, damage probability |
| `weapons` | Bullet/bomb characters, explosion radius |
| `effects` | Ripple and explosion settings |
| `gameplay` | Game speed, scoring per invader tier |

## License

MIT License. See [LICENSE](LICENSE) for details.
