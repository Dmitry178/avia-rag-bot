import { AppLayout } from "./layout/AppLayout";
import { AppProviders } from "./providers/AppProviders";

export function App() {
  return (
    <AppProviders>
      <AppLayout />
    </AppProviders>
  );
}
