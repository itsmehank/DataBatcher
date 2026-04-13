type Props = {
  previousTicker: string | null;
  nextTicker: string | null;
  disabled?: boolean;
  onSelectTicker: (ticker: string) => void;
};

export default function TickerPager({ previousTicker, nextTicker, disabled = false, onSelectTicker }: Props) {
  return (
    <div className="ticker-pager no-export" aria-label="Ticker navigation">
      <button
        type="button"
        className="ticker-pager-button"
        onClick={() => previousTicker && onSelectTicker(previousTicker)}
        disabled={disabled || !previousTicker}
      >
        ← Prev
      </button>
      <button
        type="button"
        className="ticker-pager-button"
        onClick={() => nextTicker && onSelectTicker(nextTicker)}
        disabled={disabled || !nextTicker}
      >
        Next →
      </button>
    </div>
  );
}
