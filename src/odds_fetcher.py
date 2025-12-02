"""
Betting Odds Fetcher for Premier League Fixtures

This module fetches betting odds from various APIs and calculates probabilities.
"""
import os
import requests
from typing import Dict, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class OddsFetcher:
    """Fetch betting odds from various sources"""
    
    def __init__(self, api_key: Optional[str] = None, source: str = "odds_api"):
        """
        Initialize odds fetcher
        
        Args:
            api_key: API key for the odds service
            source: Which API to use ('odds_api', 'api_football', 'norsk_tipping', or 'mock')
        """
        self.api_key = api_key or os.getenv("ODDS_API_KEY")
        self.source = source
        
    def fetch_premier_league_odds(self) -> List[Dict]:
        """
        Fetch odds for all Premier League matches
        
        Returns:
            List of fixtures with odds data
        """
        if self.source == "odds_api":
            return self._fetch_from_odds_api()
        elif self.source == "api_football":
            return self._fetch_from_api_football()
        elif self.source == "norsk_tipping":
            return self._fetch_from_norsk_tipping()
        elif self.source == "mock":
            return self._fetch_mock_odds()
        else:
            raise ValueError(f"Unknown odds source: {self.source}")
    
    def _fetch_from_odds_api(self) -> List[Dict]:
        """
        Fetch from The Odds API (https://the-odds-api.com/)
        
        Free tier: 500 requests/month
        """
        if not self.api_key:
            logger.warning("No API key provided for The Odds API")
            return []
        
        url = "https://api.the-odds-api.com/v4/sports/soccer_epl/odds"
        params = {
            "apiKey": self.api_key,
            "regions": "uk",  # UK bookmakers
            "markets": "h2h",  # Head-to-head (match winner)
            "oddsFormat": "decimal"
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            # Check remaining requests
            remaining = response.headers.get('x-requests-remaining', 'unknown')
            logger.info(f"Odds API requests remaining: {remaining}")
            
            return self._parse_odds_api_response(data)
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching from Odds API: {e}")
            return []
    
    def _parse_odds_api_response(self, data: List[Dict]) -> List[Dict]:
        """Parse response from The Odds API"""
        fixtures = []
        
        for game in data:
            home_team = game.get('home_team')
            away_team = game.get('away_team')
            commence_time = game.get('commence_time')
            
            # Get best odds from all bookmakers
            bookmakers = game.get('bookmakers', [])
            if not bookmakers:
                continue
            
            # Average odds across bookmakers
            home_odds_list = []
            draw_odds_list = []
            away_odds_list = []
            
            for bookmaker in bookmakers:
                markets = bookmaker.get('markets', [])
                for market in markets:
                    if market.get('key') == 'h2h':
                        outcomes = market.get('outcomes', [])
                        for outcome in outcomes:
                            name = outcome.get('name')
                            price = outcome.get('price')
                            
                            if name == home_team:
                                home_odds_list.append(price)
                            elif name == away_team:
                                away_odds_list.append(price)
                            elif name == 'Draw':
                                draw_odds_list.append(price)
            
            # Calculate average odds
            home_odds = sum(home_odds_list) / len(home_odds_list) if home_odds_list else None
            draw_odds = sum(draw_odds_list) / len(draw_odds_list) if draw_odds_list else None
            away_odds = sum(away_odds_list) / len(away_odds_list) if away_odds_list else None
            
            # Calculate implied probabilities
            probs = self._calculate_probabilities(home_odds, draw_odds, away_odds)
            
            fixtures.append({
                'home_team': home_team,
                'away_team': away_team,
                'commence_time': commence_time,
                'home_win_odds': home_odds,
                'draw_odds': draw_odds,
                'away_win_odds': away_odds,
                'home_win_probability': probs['home'],
                'draw_probability': probs['draw'],
                'away_win_probability': probs['away']
            })
        
        return fixtures
    
    def _fetch_from_api_football(self) -> List[Dict]:
        """
        Fetch from API-Football (https://www.api-football.com/)
        
        Free tier: 100 requests/day
        """
        if not self.api_key:
            logger.warning("No API key provided for API-Football")
            return []
        
        # Get current season and Premier League ID (39)
        url = "https://v3.football.api-sports.io/odds"
        headers = {
            'x-rapidapi-key': self.api_key,
            'x-rapidapi-host': 'v3.football.api-sports.io'
        }
        params = {
            'league': 39,  # Premier League
            'season': datetime.now().year,
            'bet': 1  # Match Winner
        }
        
        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            return self._parse_api_football_response(data)
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching from API-Football: {e}")
            return []
    
    def _parse_api_football_response(self, data: Dict) -> List[Dict]:
        """Parse response from API-Football"""
        fixtures = []
        
        response = data.get('response', [])
        for game in response:
            fixture = game.get('fixture', {})
            teams = game.get('teams', {})
            bookmakers = game.get('bookmakers', [])
            
            if not bookmakers:
                continue
            
            # Get odds from first bookmaker (or average if needed)
            odds_data = bookmakers[0].get('bets', [])
            for bet in odds_data:
                if bet.get('name') == 'Match Winner':
                    values = bet.get('values', [])
                    
                    home_odds = None
                    draw_odds = None
                    away_odds = None
                    
                    for value in values:
                        odd_type = value.get('value')
                        odd_price = float(value.get('odd', 0))
                        
                        if odd_type == 'Home':
                            home_odds = odd_price
                        elif odd_type == 'Draw':
                            draw_odds = odd_price
                        elif odd_type == 'Away':
                            away_odds = odd_price
                    
                    probs = self._calculate_probabilities(home_odds, draw_odds, away_odds)
                    
                    fixtures.append({
                        'fixture_id': fixture.get('id'),
                        'home_team': teams.get('home', {}).get('name'),
                        'away_team': teams.get('away', {}).get('name'),
                        'commence_time': fixture.get('date'),
                        'home_win_odds': home_odds,
                        'draw_odds': draw_odds,
                        'away_win_odds': away_odds,
                        'home_win_probability': probs['home'],
                        'draw_probability': probs['draw'],
                        'away_win_probability': probs['away']
                    })
        
        return fixtures
    
    def _fetch_from_norsk_tipping(self) -> List[Dict]:
        """
        Fetch odds with European/Norwegian bookmakers prioritized
        
        Instead of scraping Norsk Tipping (which doesn't have a public API),
        this uses The Odds API with European bookmakers that operate in Norway.
        
        Bookmakers included: Betsson, Unibet, Bet365, etc.
        """
        logger.info("Fetching odds from European bookmakers (Norway-friendly)...")
        
        # Use The Odds API with European bookmakers
        if self.api_key:
            return self._fetch_from_odds_api_norwegian()
        else:
            logger.warning("No API key provided. Using mock data for demonstration.")
            logger.info("Get a free API key at https://the-odds-api.com/ (500 requests/month)")
            return self._fetch_mock_odds()
    
    def _fetch_from_odds_api_norwegian(self) -> List[Dict]:
        """
        Fetch Premier League odds from The Odds API with European bookmakers
        
        Uses UK and European bookmakers including those operating in Norway.
        More reliable than scraping and provides quality odds data.
        """
        if not self.api_key:
            logger.warning("No API key provided for The Odds API")
            return []
        
        url = "https://api.the-odds-api.com/v4/sports/soccer_epl/odds"
        params = {
            "apiKey": self.api_key,
            "regions": "uk,eu",  # UK and European bookmakers
            "markets": "h2h",
            "oddsFormat": "decimal"
        }
        
        try:
            logger.info(f"Requesting odds from The Odds API (regions: uk,eu)...")
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Check remaining requests
            remaining = response.headers.get('x-requests-remaining', 'unknown')
            logger.info(f"✓ Odds API requests remaining: {remaining}")
            
            if not data:
                logger.warning("No odds data returned from API")
                return []
            
            logger.info(f"✓ Retrieved odds for {len(data)} matches")
            
            # Parse the response
            return self._parse_odds_api_response(data)
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching from Odds API: {e}")
            logger.info("Tip: Check your API key at https://the-odds-api.com/account")
            return []
    
    def _filter_norwegian_bookmakers(self, data: List[Dict]) -> List[Dict]:
        """
        Filter odds data to prioritize Norwegian bookmakers
        
        Common Norwegian bookmakers: Norsk Tipping, Betsson, Unibet Norge, etc.
        """
        norwegian_bookmakers = [
            'norsk_tipping',
            'betsson',
            'unibet',
            'betsafe',
            'mrgreen',
            'rizk',
            'bet365'  # Also operates in Norway
        ]
        
        filtered_data = []
        for game in data:
            bookmakers = game.get('bookmakers', [])
            norwegian_bookmakers_only = [
                bm for bm in bookmakers 
                if any(nb in bm.get('key', '').lower() for nb in norwegian_bookmakers)
            ]
            
            if norwegian_bookmakers_only:
                game_copy = game.copy()
                game_copy['bookmakers'] = norwegian_bookmakers_only
                filtered_data.append(game_copy)
            else:
                # Keep all bookmakers if no Norwegian ones found
                filtered_data.append(game)
        
        return filtered_data
    
    def _fetch_mock_odds(self) -> List[Dict]:
        """Generate mock odds for testing (no API key required)"""
        import random
        
        # Mock data for demonstration
        mock_fixtures = [
            {'home_team': 'Arsenal', 'away_team': 'Liverpool'},
            {'home_team': 'Man City', 'away_team': 'Chelsea'},
            {'home_team': 'Spurs', 'away_team': 'Man Utd'},
        ]
        
        fixtures = []
        for fixture in mock_fixtures:
            # Generate realistic-looking odds
            home_odds = round(random.uniform(1.5, 4.0), 2)
            draw_odds = round(random.uniform(3.0, 4.5), 2)
            away_odds = round(random.uniform(1.5, 5.0), 2)
            
            probs = self._calculate_probabilities(home_odds, draw_odds, away_odds)
            
            fixtures.append({
                'home_team': fixture['home_team'],
                'away_team': fixture['away_team'],
                'commence_time': datetime.now().isoformat(),
                'home_win_odds': home_odds,
                'draw_odds': draw_odds,
                'away_win_odds': away_odds,
                'home_win_probability': probs['home'],
                'draw_probability': probs['draw'],
                'away_win_probability': probs['away']
            })
        
        return fixtures
    
    @staticmethod
    def _calculate_probabilities(home_odds: Optional[float], 
                                 draw_odds: Optional[float], 
                                 away_odds: Optional[float]) -> Dict[str, Optional[float]]:
        """
        Calculate implied probabilities from decimal odds
        
        Decimal odds formula: probability = 1 / odds
        We also remove the bookmaker's margin (overround)
        """
        if not all([home_odds, draw_odds, away_odds]):
            return {'home': None, 'draw': None, 'away': None}
        
        # Calculate raw probabilities
        home_prob = 1 / home_odds
        draw_prob = 1 / draw_odds
        away_prob = 1 / away_odds
        
        # Total probability (includes bookmaker margin)
        total = home_prob + draw_prob + away_prob
        
        # Normalize to remove margin (so probabilities sum to 1.0)
        return {
            'home': round(home_prob / total, 4),
            'draw': round(draw_prob / total, 4),
            'away': round(away_prob / total, 4)
        }
    
    def match_with_fpl_fixtures(self, odds_data: List[Dict], fpl_fixtures: List[Dict]) -> List[Dict]:
        """
        Match odds data with FPL fixtures
        
        Args:
            odds_data: Odds data from betting API
            fpl_fixtures: Fixtures from FPL API
            
        Returns:
            FPL fixtures enriched with odds data
        """
        # Create a mapping of team names (odds API names might differ from FPL)
        team_name_mapping = self._get_team_name_mapping()
        
        enriched_fixtures = []
        for fpl_fixture in fpl_fixtures:
            fpl_home = fpl_fixture.get('team_h_name', '')
            fpl_away = fpl_fixture.get('team_a_name', '')
            
            # Find matching odds data
            matched_odds = None
            for odds in odds_data:
                odds_home = team_name_mapping.get(odds['home_team'], odds['home_team'])
                odds_away = team_name_mapping.get(odds['away_team'], odds['away_team'])
                
                if odds_home == fpl_home and odds_away == fpl_away:
                    matched_odds = odds
                    break
            
            # Merge data
            enriched = fpl_fixture.copy()
            if matched_odds:
                enriched.update({
                    'home_win_odds': matched_odds.get('home_win_odds'),
                    'draw_odds': matched_odds.get('draw_odds'),
                    'away_win_odds': matched_odds.get('away_win_odds'),
                    'home_win_probability': matched_odds.get('home_win_probability'),
                    'draw_probability': matched_odds.get('draw_probability'),
                    'away_win_probability': matched_odds.get('away_win_probability')
                })
            
            enriched_fixtures.append(enriched)
        
        return enriched_fixtures
    
    @staticmethod
    def _get_team_name_mapping() -> Dict[str, str]:
        """
        Map betting API team names to FPL team names
        Different APIs may use different naming conventions
        """
        return {
            # Odds API -> FPL naming (from bootstrap-static API)
            'Manchester City': 'Man City',
            'Manchester United': 'Man Utd',
            'Tottenham Hotspur': 'Spurs',
            'Newcastle United': 'Newcastle',
            'Nottingham Forest': "Nott'm Forest",
            'West Ham United': 'West Ham',
            'Wolverhampton Wanderers': 'Wolves',
            'Brighton and Hove Albion': 'Brighton',
            'Leicester City': 'Leicester',
            'Ipswich Town': 'Ipswich',
            'Luton Town': 'Luton',
            'Sheffield United': 'Sheffield Utd',
            # Reverse mapping for FPL -> Odds API
            'Man City': 'Manchester City',
            'Man Utd': 'Manchester United',
            'Spurs': 'Tottenham Hotspur',
            'Newcastle': 'Newcastle United',
            "Nott'm Forest": 'Nottingham Forest',
            'West Ham': 'West Ham United',
            'Wolves': 'Wolverhampton Wanderers',
            'Brighton': 'Brighton and Hove Albion',
        }


# Example usage
if __name__ == "__main__":
    # Test with mock data
    fetcher = OddsFetcher(source="mock")
    odds = fetcher.fetch_premier_league_odds()
    
    print("Fetched odds for Premier League matches:")
    for fixture in odds:
        print(f"\n{fixture['home_team']} vs {fixture['away_team']}")
        print(f"  Home Win: {fixture['home_win_odds']} (prob: {fixture['home_win_probability']:.1%})")
        print(f"  Draw: {fixture['draw_odds']} (prob: {fixture['draw_probability']:.1%})")
        print(f"  Away Win: {fixture['away_win_odds']} (prob: {fixture['away_win_probability']:.1%})")

