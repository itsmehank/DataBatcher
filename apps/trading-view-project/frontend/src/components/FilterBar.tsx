import type { Region } from "../types";

type Props = {
  region: Region;
  date: string;
  market: string;
  category: string;
  symbol: string;
  disabled?: boolean;
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
  disabled,
}: {
  label: string;
  value: string;
  options: string[];
  onChange: (value: string) => void;
  disabled?: boolean;
}) {
  return (
    <label className="filter-item">
      <span>{label}</span>
      <select value={value} onChange={(e) => onChange(e.target.value)} disabled={disabled}>
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
        disabled={props.disabled}
        onChange={(value) => props.onChange("region", value)}
      />
      <SelectField
        label="Date"
        value={props.date}
        options={props.dates}
        disabled={props.disabled}
        onChange={(value) => props.onChange("date", value)}
      />
      <SelectField
        label="Market"
        value={props.market}
        options={props.markets}
        disabled={props.disabled}
        onChange={(value) => props.onChange("market", value)}
      />
      <SelectField
        label="Category"
        value={props.category}
        options={props.categories}
        disabled={props.disabled}
        onChange={(value) => props.onChange("category", value)}
      />
      <SelectField
        label="Ticker"
        value={props.symbol}
        options={props.symbols}
        disabled={props.disabled}
        onChange={(value) => props.onChange("symbol", value)}
      />
    </section>
  );
}
