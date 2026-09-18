class ValueEngine:
    """
    Value Engine — анализирует коэффициенты и находит переоценённые/недооценённые события
    """
    
    def __init__(self):
        self.vig = 0.05  # стандартная маржа букмекера ~5%
    
    def no_vig_probability(self, odds1, odds2):
        """
        Вычисляет no-vig вероятность
        """
        prob1 = 1 / odds1
        prob2 = 1 / odds2
        total = prob1 + prob2
        return {
            "p1": prob1 / total,
            "p2": prob2 / total,
            "vig": total - 1
        }
    
    def evaluate(self, win_prob, odds1, odds2):
        """
        Оценивает Value (EV) для ставки на P1 и P2
        """
        no_vig = self.no_vig_probability(odds1, odds2)
        
        # Вычисляем EV для P1
        ev_p1 = win_prob * (odds1 - 1) - (1 - win_prob)
        ev_p2 = (1 - win_prob) * (odds2 - 1) - win_prob
        
        # Определяем сигнал
        signal = None
        if ev_p1 > 0.05:
            signal = f"🔴 Value на {no_vig['p1']*100:.1f}% (EV = {ev_p1*100:.1f}%)"
        elif ev_p2 > 0.05:
            signal = f"🔴 Value на {no_vig['p2']*100:.1f}% (EV = {ev_p2*100:.1f}%)"
        else:
            signal = "✅ Нет явного Value"
        
        return {
            "no_vig_prob": no_vig['p1'],
            "vig": no_vig['vig'],
            "ev_p1": ev_p1,
            "ev_p2": ev_p2,
            "signal": signal,
            "edge": max(ev_p1, ev_p2) * 100 if max(ev_p1, ev_p2) > 0 else 0
        }