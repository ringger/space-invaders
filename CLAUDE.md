# Space Invaders Game - Development Priorities

## Current Todo List

### ✅ Completed Features
- Basic game structure with curses
- Player ship with movement and shooting
- Invader formation with animated sprites
- Destructible barriers/bunkers
- UFO bonus ship implementation  
- Lives system (3 lives)
- Color cycling and ripple effects
- Wing-flapping animations
- Alien bombs with blast radius
- Screen flickering reduction
- Terminal resize handling
- Configuration system (config.json)
- Different point values for invader types (30/20/10 pts)

### 📋 Pending Tasks (Priority Order)

1. **Add player death animation with explosion effect**
   - Visual feedback when player is hit
   - Brief explosion animation before respawn

2. **Limit player to 1-2 bullets on screen at once**
   - Prevents bullet spam
   - More strategic gameplay like original

3. **Implement invader death animation with explosion effect**
   - Visual feedback when invaders are destroyed
   - Brief explosion before removal

4. **Add high score tracking to score display**
   - Persistent high score storage
   - Display current vs high score

5. **Improve level progression with invaders starting lower each level**
   - Increases difficulty progressively
   - Makes later levels more challenging

## Development Notes
- Game uses Python curses library for terminal graphics
- All constants configurable via config.json
- Testing requires actual terminal (curses limitations in some environments)