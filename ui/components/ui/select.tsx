"use client"

import * as React from "react"
import { ChevronDown, Check } from "lucide-react"
import { cn } from "../../lib/utils"

interface Option {
  label: string
  value: string
  disabled?: boolean
}

interface SelectProps extends Omit<React.HTMLAttributes<HTMLDivElement>, 'value' | 'onChange'> {
  value?: string
  onChange?: (value: string) => void
  placeholder?: string
  options: Option[]
  disabled?: boolean
}

const Select = React.forwardRef<HTMLDivElement, SelectProps>(
  ({ className, value, onChange, placeholder = "Select an option", options, disabled, ...props }, ref) => {
    const [isOpen, setIsOpen] = React.useState(false)
    const [highlightedIndex, setHighlightedIndex] = React.useState(-1)
    const containerRef = React.useRef<HTMLDivElement>(null)
    const selectedOption = options.find(opt => opt.value === value)

    const handleClick = () => {
      if (!disabled) {
        setIsOpen(!isOpen)
      }
    }

    const handleOptionClick = (option: Option) => {
      if (!option.disabled) {
        onChange?.(option.value)
        setIsOpen(false)
      }
    }

    const handleKeyDown = (event: React.KeyboardEvent) => {
      if (disabled) return

      switch (event.key) {
        case "Enter":
        case " ":
          event.preventDefault()
          if (!isOpen) {
            setIsOpen(true)
          } else if (highlightedIndex >= 0) {
            const option = options[highlightedIndex]
            if (!option.disabled) {
              handleOptionClick(option)
            }
          }
          break
        case "ArrowDown":
          event.preventDefault()
          if (!isOpen) {
            setIsOpen(true)
          } else {
            setHighlightedIndex(prev => 
              prev < options.length - 1 ? prev + 1 : prev
            )
          }
          break
        case "ArrowUp":
          event.preventDefault()
          if (!isOpen) {
            setIsOpen(true)
          } else {
            setHighlightedIndex(prev => 
              prev > 0 ? prev - 1 : prev
            )
          }
          break
        case "Escape":
          setIsOpen(false)
          break
      }
    }

    React.useEffect(() => {
      const handleClickOutside = (event: MouseEvent) => {
        if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
          setIsOpen(false)
        }
      }

      document.addEventListener("mousedown", handleClickOutside)
      return () => document.removeEventListener("mousedown", handleClickOutside)
    }, [])

    return (
      <div
        ref={containerRef}
        className={cn("relative w-full", className)}
        {...props}
      >
        <div
          ref={ref}
          role="combobox"
          aria-expanded={isOpen}
          aria-haspopup="listbox"
          aria-controls="select-dropdown"
          tabIndex={disabled ? -1 : 0}
          className={cn(
            "flex h-10 w-full items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
            disabled && "cursor-not-allowed opacity-50",
            !disabled && "cursor-pointer"
          )}
          onClick={handleClick}
          onKeyDown={handleKeyDown}
        >
          <span className="flex-1 truncate">
            {selectedOption ? selectedOption.label : placeholder}
          </span>
          <ChevronDown className="h-4 w-4 opacity-50" />
        </div>

        {isOpen && (
          <div
            id="select-dropdown"
            role="listbox"
            aria-label="Options"
            className="absolute z-50 mt-1 max-h-60 w-full overflow-auto rounded-md border bg-popover text-popover-foreground shadow-md"
          >
            <div className="p-1">
              {options.map((option, index) => (
                <div
                  key={option.value}
                  role="option"
                  aria-selected={value === option.value}
                  aria-disabled={option.disabled}
                  tabIndex={-1}
                  className={cn(
                    "relative flex w-full cursor-default select-none items-center rounded-sm py-1.5 pl-8 pr-2 text-sm outline-none",
                    value === option.value && "bg-accent text-accent-foreground",
                    highlightedIndex === index && "bg-accent text-accent-foreground",
                    option.disabled && "pointer-events-none opacity-50",
                    !option.disabled && "cursor-pointer hover:bg-accent hover:text-accent-foreground"
                  )}
                  onClick={() => handleOptionClick(option)}
                >
                  {value === option.value && (
                    <span className="absolute left-2 flex h-3.5 w-3.5 items-center justify-center">
                      <Check className="h-4 w-4" />
                    </span>
                  )}
                  {option.label}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    )
  }
)
Select.displayName = "Select"

export { Select }
export type { Option as SelectOption } 