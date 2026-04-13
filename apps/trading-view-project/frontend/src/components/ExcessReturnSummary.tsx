import type { ExcessReturnCard } from "../lib/excessReturns";

type Props = {
  cards: ExcessReturnCard[];
};

const formatPct = (value: number | null) => (value === null ? "N/A" : `${value > 0 ? "+" : ""}${value.toFixed(2)}%`);

export default function ExcessReturnSummary({ cards }: Props) {
  return (
    <section className="panel excess-return-panel">
      <div className="panel-header">
        <h2>Benchmark Relative Return</h2>
        <span>{cards[0]?.benchmarkLabel ?? "Benchmark"} 기준</span>
      </div>
      <div className="excess-return-grid">
        {cards.map((card) => {
          const tone = card.excessReturn === null ? "neutral" : card.excessReturn >= 0 ? "positive" : "negative";
          return (
            <article key={card.label} className={`excess-return-card ${tone}`}>
              <span className="period-label">{card.label}</span>
              <strong>{formatPct(card.excessReturn)}</strong>
              <p>
                Stock {formatPct(card.symbolReturn)} / {card.benchmarkLabel} {formatPct(card.benchmarkReturn)}
              </p>
            </article>
          );
        })}
      </div>
    </section>
  );
}
