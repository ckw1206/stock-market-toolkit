import {
  Select, SelectTrigger, SelectValue, SelectContent, SelectItem,
} from "frontend";

const items = (
  <SelectContent>
    <SelectItem value="1d">1 Day</SelectItem>
    <SelectItem value="1w">1 Week</SelectItem>
    <SelectItem value="1m">1 Month</SelectItem>
    <SelectItem value="1y">1 Year</SelectItem>
  </SelectContent>
);

export const Closed = () => (
  <div className="bg-background text-foreground p-6">
    <Select defaultValue="1d">
      <SelectTrigger className="w-40"><SelectValue /></SelectTrigger>
      {items}
    </Select>
  </div>
);

export const Open = () => (
  <div className="bg-background text-foreground p-6" style={{ minHeight: 260 }}>
    <Select defaultOpen defaultValue="1w">
      <SelectTrigger className="w-40"><SelectValue /></SelectTrigger>
      {items}
    </Select>
  </div>
);
