import { Button } from "@/components/ui/button"

function App() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 p-4">
      <h1 className="text-4xl font-bold">React Generator Base</h1>
      <p className="text-muted-foreground">
        This is the base template for generated applications.
      </p>
      <Button>Click me</Button>
    </div>
  )
}

export default App
