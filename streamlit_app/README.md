# Streamlit App - Modular Structure

## Overview
The Fantasy Football Analytics Dashboard has been refactored into a modular structure for better maintainability and organization.

## Directory Structure

```
streamlit_app/
├── __init__.py              # Package initialization
├── config.py                # Configuration and constants
├── utils.py                 # Data fetching and helper functions
├── main.py                  # Main application entry point
├── tabs/                    # Tab modules
│   ├── __init__.py
│   ├── leaderboard.py       # Leaderboard tab
│   ├── performance_trends.py # Performance trends tab
│   ├── transfer_analysis.py  # Transfer analysis tab
│   ├── managers_favorites.py # Manager's favorites tab
│   └── consistency_analysis.py # Consistency analysis tab
└── README.md                # This file
```

## File Descriptions

### `config.py`
Contains all configuration and constants:
- **PREMIER_LEAGUE_COLORS**: Official team colors for all PL teams
- **CUSTOM_CSS**: Streamlit custom styling
- **CDF Configuration**: Space, version, and view IDs
- **CACHE_TTL**: Data caching time-to-live

### `utils.py`
Core utility functions:
- **`get_cdf_client()`**: Initialize CDF client connection
- **Data fetching functions**: 
  - `fetch_managers()`: Get all managers
  - `fetch_performance_data()`: Get gameweek performance
  - `fetch_team_betting_data()`: Get team preference data
  - `fetch_teams()`: Get Premier League teams
  - `fetch_transfer_data()`: Get transfer history
  - `fetch_players()`: Get player data
  - `fetch_player_picks_from_raw()`: Get raw pick data
- **Helper functions**:
  - `get_team_color()`: Get team's official color
  - `create_team_badge()`: Create colored HTML badge

### `main.py`
Main application orchestrator:
- Sets up Streamlit page configuration
- Initializes CDF client
- Fetches shared data
- Creates sidebar filters
- Renders all tabs

### Tab Modules

#### `tabs/leaderboard.py`
- League rankings
- Key metrics (total managers, highest points, etc.)
- Points distribution visualization

#### `tabs/performance_trends.py`
- Weekly performance charts
- Cumulative points tracking
- Transfer activity visualization

#### `tabs/transfer_analysis.py`
- Transfer success metrics
- Manager-wise transfer stats
- Net benefit analysis
- Recent transfers table

#### `tabs/managers_favorites.py`
- **Most comprehensive tab** with Premier League team colors
- Team preference overview
- Most picked vs most valuable analysis
- Individual manager deep dive
- Player lists from favorite teams
- Manager x Team heatmap
- Complete team summary

#### `tabs/consistency_analysis.py`
- Consistency score analysis
- Volatility vs average points
- Team value growth correlation
- Category leaders

## Usage

### Running the App

From the project root:
```bash
streamlit run streamlit_app.py
```

### Adding a New Tab

1. Create new file in `tabs/` directory:
```python
# tabs/my_new_tab.py
import streamlit as st

def render(client, managers_df, **kwargs):
    """Render the new tab"""
    st.header("My New Tab")
    st.write("Content here...")
```

2. Import in `main.py`:
```python
from .tabs import my_new_tab
```

3. Add tab to main app:
```python
tab6 = st.tabs(["...", "🆕 My New Tab"])
with tab6:
    my_new_tab.render(client, managers_df)
```

### Modifying Configurations

Edit `config.py` to:
- Add/update team colors
- Change CDF configuration
- Modify cache settings
- Update custom CSS

### Adding New Data Fetching Functions

Add to `utils.py`:
```python
@st.cache_data(ttl=CACHE_TTL)
def fetch_my_data(_client):
    """Fetch my custom data"""
    # Implementation here
    return data
```

## Benefits of Modular Structure

### 1. **Maintainability**
- Each tab is self-contained
- Easy to find and edit specific features
- Clear separation of concerns

### 2. **Scalability**
- Adding new tabs is straightforward
- No risk of creating merge conflicts
- Easy to collaborate on different features

### 3. **Testability**
- Each module can be tested independently
- Easier to write unit tests
- Clear function boundaries

### 4. **Reusability**
- Utility functions are centralized
- Consistent data fetching across tabs
- Shared configuration management

### 5. **Code Organization**
- ~1200 lines split into manageable files
- Each file has a single responsibility
- Clear imports and dependencies

## Development Guidelines

### Adding Features
1. Identify the appropriate module (tab/utils/config)
2. Follow existing patterns
3. Keep functions focused and small
4. Document complex logic

### Styling
- Use team colors from `config.PREMIER_LEAGUE_COLORS`
- Apply badges via `create_team_badge()` function
- Follow existing Plotly chart patterns

### Data Fetching
- Always use `@st.cache_data` decorator
- Pass client as `_client` to avoid caching issues
- Handle errors gracefully with try/except

### Performance
- Minimize data fetching in render functions
- Use expanders for optional/debug content
- Leverage Streamlit's caching effectively

## Migration Notes

The old `streamlit_app.py` (1200+ lines) has been backed up to `streamlit_app_old.py`. 

Key changes:
- ✅ All functionality preserved
- ✅ Enhanced Manager's Favorites tab
- ✅ Added debug expanders
- ✅ Better error handling
- ✅ Cleaner imports
- ✅ Easier to extend

## Troubleshooting

### Import Errors
If you see import errors, ensure you're running from the project root:
```bash
cd /path/to/fantasy-football
streamlit run streamlit_app.py
```

### Module Not Found
Make sure all `__init__.py` files exist:
```bash
ls streamlit_app/__init__.py
ls streamlit_app/tabs/__init__.py
```

### Cache Issues
Clear Streamlit cache if data seems stale:
- Press `C` in the running app
- Or restart the app

## Future Enhancements

Potential additions to consider:
- [ ] Add authentication module
- [ ] Create shared components folder
- [ ] Add data validation utilities
- [ ] Implement error logging
- [ ] Add configuration file loading
- [ ] Create API wrapper module
- [ ] Add chart theming module

## Support

For issues or questions about the modular structure:
1. Check this README first
2. Review code comments in each module
3. Refer to the original documentation

---

**Version**: 2.0.0  
**Last Updated**: November 2025  
**Structure By**: Modular refactoring

