import type { Region } from "../types";

type Props = {
  region: Region;
  date: string;
  market: string;
  category: string;
  symbol: string;
  regions: Region[];
  dates: string[];
  markets: string[];
  categories: string[];
  symbols: string[];
  onChange: (key: "region" | "date" | "market" | "category" | "symbol", value: string) => void;
};

function SelectField({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: string;
  options: string[];
  onChange: (value: string) => void;
}) {
  return (
    <label className="filter-item">
      <span>{label}</span>
      <select value={value} onChange={(e) => onChange(e.target.value)}>
        {options.map((opt) => (
          <option key={opt} value={opt}>
            {opt}
          </option>
        ))}
      </select>
    </label>
  );
}

export default function FilterBar(props: Props) {
  return (
    <section className="filter-bar">
      <SelectField
        label="Region"
        value={props.region}
        options={props.regions}
        onChange={(value) => props.onChange("region", value)}
      />
      <SelectField label="Date" value={props.date} options={props.dates} onChange={(value) => props.onChange("date", value)} />
      <SelectField
        label="Market"
        value={props.market}
        options={props.markets}
        onChange={(value) => props.onChange("market", value)}
      />
      <SelectField
        label="Category"
        value={props.category}
        options={props.categories}
        onChange={(value) => props.onChange("category", value)}
      />
      <SelectField
        label="Ticker"
        value={props.symbol}
        options={props.symbols}
        onChange={(value) => props.onChange("symbol", value)}
      />
    </section>
  );
}
