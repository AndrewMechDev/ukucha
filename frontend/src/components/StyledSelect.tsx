import { useEffect, useRef, useState } from "react";

type SelectOption = {
  label: string;
  value: string;
};

type StyledSelectProps = {
  value: string;
  options: SelectOption[];
  onChange: (value: string) => void;
  ariaLabel: string;
};

export default function StyledSelect({ value, options, onChange, ariaLabel }: StyledSelectProps) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const selected = options.find((option) => option.value === value) ?? options[0];

  useEffect(() => {
    const handlePointerDown = (event: PointerEvent) => {
      if (rootRef.current && !rootRef.current.contains(event.target as Node)) setOpen(false);
    };

    document.addEventListener("pointerdown", handlePointerDown);
    return () => document.removeEventListener("pointerdown", handlePointerDown);
  }, []);

  return (
    <div className={`styled-select${open ? " is-open" : ""}`} ref={rootRef}>
      <button
        className="styled-select__trigger"
        type="button"
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-label={ariaLabel}
        onClick={() => setOpen((isOpen) => !isOpen)}
        onKeyDown={(event) => {
          if (event.key === "Escape") setOpen(false);
        }}
      >
        <span>{selected?.label}</span>
        <span className="material-symbols-rounded" aria-hidden="true">expand_more</span>
      </button>
      {open && (
        <div className="styled-select__menu" role="listbox" aria-label={ariaLabel}>
          {options.map((option) => (
            <button
              className={`styled-select__option${option.value === value ? " is-selected" : ""}`}
              type="button"
              role="option"
              aria-selected={option.value === value}
              onClick={() => {
                onChange(option.value);
                setOpen(false);
              }}
              key={option.value}
            >
              <span>{option.label}</span>
              {option.value === value && <span className="material-symbols-rounded" aria-hidden="true">check</span>}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
