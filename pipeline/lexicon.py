"""Dictionnaires de sentiment financier.

Anglais : sous-ensemble des mots les plus fréquents en presse financière du dictionnaire
Loughran-McDonald (2011), complété par le vocabulaire des marchés.
Français : dictionnaire construit pour le projet. Les entrées sont des racines :
« hauss » couvre hausse, haussier, haussière…
"""

FR_POS = """
hauss envol rebond rebondi bondi bond progress grimp redress reprise repris record sommet
embellie optimis confian solide robust dynam vigueur vigoureu fort accélér croissan
amélior favorab positi gagn gain bénéfic profit rentab surperform rallye flamb
soutien soutenu stimul relanc apais détente détend accalmi stabil rassur sereinement
accord entente cessez-le-feu trêve compromis apaisement résilien rattrap décoll
dépass meilleur battu supérieur excédent embauch créations recrut plein-emploi
baisse_des_taux assoupl dividende rachat succès percée innov expansion essor boom
attractif opportun haussier euphori enthousias porteur prometteu encourag réjoui
""".split()

FR_NEG = """
baiss chut recul repli plong effondr krach dégringol décroch déviss lourd plonge
crise récession contraction ralenti stagn stagflation déflation inflationniste
pessimis inquiét crainte craint peur panique angoiss nervosit tension tendu volatil
incertitud risqu menac danger alerte avertiss prudence prudent fragil vulnérab
faibl dégrad détérior affaibl perte pertes déficit dette endett faillite défaut
insolvab liquidation licenci chômage suppressions plan_social fermeture grève
sanction guerre conflit attaque invasion bombard escalade terroris instabil
protectionn droits_de_douane tarif taxe_douanière embargo boycott
déçu décevan déception manqu raté inférieur avertissement_sur_résultats
resserr durciss hausse_des_taux restricti chute_libre correction baissier
scandale fraude enquête amende poursuite litige cyberattaque piratage
démission chaos blocage shutdown paralysie pénurie choc tourmente turbulen
""".split()

EN_POS = """
gain gains rally rallies rallied surge surged soar soared jump jumped rebound rebounded
record high highs beat beats outperform outperformed strong stronger strength robust
growth grow growing expand expansion boom booming upbeat optimism optimistic confident
confidence improve improved improvement recover recovery positive profit profitable
upgrade upgraded bullish boost boosted rise rising rose climb climbed advance advanced
easing ease eased cut_rates stimulus deal agreement truce ceasefire breakthrough
stabilize stable resilient resilience exceed exceeded surpass momentum favorable
success successful innovative opportunity hiring hire jobs_growth dividend buyback
""".split()

EN_NEG = """
loss losses fall falls fell drop dropped decline declined slump slumped plunge plunged
tumble tumbled crash crashed sell-off selloff slide slid sink sank weak weaker weakness
recession contraction slowdown slow slowing stagnation stagflation deflation downturn
fear fears worry worries worried concern concerns anxiety panic turmoil volatile volatility
uncertain uncertainty risk risks risky threat threaten warning warn warned caution
crisis default bankruptcy bankrupt insolvency debt deficit layoff layoffs cuts job_cuts
unemployment downgrade downgraded bearish miss missed disappoint disappointing
war conflict attack invasion sanctions tariff tariffs trade_war escalation tension tensions
hike hikes hawkish tightening inflationary shortage shock collapse collapsed fraud probe
lawsuit fine scandal shutdown strike protest unrest instability fragile vulnerable
""".split()

NEGATIONS_FR = {"pas", "ni", "sans", "aucun", "aucune", "jamais", "guère", "plus"}
NEGATIONS_EN = {"not", "no", "never", "without", "nor", "neither", "n't", "hardly"}

# Thèmes pour la phrase d'avis du jour
THEMES = {
    "les banques centrales": ["fed", "bce", "ecb", "powell", "lagarde", "taux", "rate", "rates", "monétaire", "monetary"],
    "l'inflation": ["inflation", "prix", "prices", "cpi", "ipc"],
    "la géopolitique": ["guerre", "war", "ukraine", "russie", "russia", "israël", "israel", "iran", "taïwan", "taiwan", "sanction", "sanctions", "otan", "nato"],
    "le commerce mondial": ["douane", "droits", "tariff", "tariffs", "commerce", "trade", "exportations", "exports"],
    "les résultats d'entreprises": ["résultats", "earnings", "bénéfice", "chiffre", "revenue", "profit", "guidance"],
    "l'énergie": ["pétrole", "oil", "brent", "opep", "opec", "gaz", "gas", "énergie", "energy"],
    "la Chine": ["chine", "china", "chinese", "chinois", "pékin", "beijing", "yuan"],
    "l'emploi": ["emploi", "jobs", "chômage", "unemployment", "payrolls", "embauches"],
    "la tech et l'IA": ["ia", "ai", "nvidia", "tech", "technologie", "semi-conducteurs", "chips", "apple", "microsoft"],
    "la dette publique": ["dette", "debt", "déficit", "deficit", "budget", "oat", "notation", "rating"],
}
