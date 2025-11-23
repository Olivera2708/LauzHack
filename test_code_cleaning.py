#!/usr/bin/env python3
"""
Test script to verify the code cleaning function works correctly.
"""

import sys
sys.path.insert(0, '.')

from app.services.junior_dev import clean_code_output

def test_clean_code_output():
    """Test various markdown code block formats."""
    
    print("Testing code cleaning function...\n")
    
    # Test 1: Code with tsx markdown tags
    test1 = """```tsx
import React from 'react'

export const Component = () => {
  return <div>Hello</div>
}
```"""
    
    expected1 = """import React from 'react'

export const Component = () => {
  return <div>Hello</div>
}"""
    
    result1 = clean_code_output(test1)
    assert result1 == expected1, f"Test 1 failed:\nExpected:\n{expected1}\n\nGot:\n{result1}"
    print("✓ Test 1 passed: tsx tags removed correctly")
    
    # Test 2: Code with typescript tags
    test2 = """```typescript
interface Props {
  name: string;
}

export const Component = ({ name }: Props) => {
  return <div>{name}</div>
}
```"""
    
    expected2 = """interface Props {
  name: string;
}

export const Component = ({ name }: Props) => {
  return <div>{name}</div>
}"""
    
    result2 = clean_code_output(test2)
    assert result2 == expected2, f"Test 2 failed:\nExpected:\n{expected2}\n\nGot:\n{result2}"
    print("✓ Test 2 passed: typescript tags removed correctly")
    
    # Test 3: Code with just ``` tags
    test3 = """```
const x = 5;
console.log(x);
```"""
    
    expected3 = """const x = 5;
console.log(x);"""
    
    result3 = clean_code_output(test3)
    assert result3 == expected3, f"Test 3 failed:\nExpected:\n{expected3}\n\nGot:\n{result3}"
    print("✓ Test 3 passed: plain ``` tags removed correctly")
    
    # Test 4: Code without markdown tags (should remain unchanged)
    test4 = """import React from 'react'

export const Component = () => {
  return <div>Hello</div>
}"""
    
    expected4 = test4
    result4 = clean_code_output(test4)
    assert result4 == expected4, f"Test 4 failed:\nExpected:\n{expected4}\n\nGot:\n{result4}"
    print("✓ Test 4 passed: code without tags unchanged")
    
    # Test 5: Code with jsx tags
    test5 = """```jsx
export default function App() {
  return <h1>Hello World</h1>
}
```"""
    
    expected5 = """export default function App() {
  return <h1>Hello World</h1>
}"""
    
    result5 = clean_code_output(test5)
    assert result5 == expected5, f"Test 5 failed:\nExpected:\n{expected5}\n\nGot:\n{result5}"
    print("✓ Test 5 passed: jsx tags removed correctly")
    
    # Test 6: Code with js tags
    test6 = """```js
function test() {
  return 42;
}
```"""
    
    expected6 = """function test() {
  return 42;
}"""
    
    result6 = clean_code_output(test6)
    assert result6 == expected6, f"Test 6 failed:\nExpected:\n{expected6}\n\nGot:\n{result6}"
    print("✓ Test 6 passed: js tags removed correctly")
    
    print("\n🎉 All tests passed! Code cleaning works correctly.")
    return True

if __name__ == "__main__":
    try:
        if test_clean_code_output():
            print("\n✅ Code cleaning function is ready to use.")
            sys.exit(0)
        else:
            print("\n❌ Some tests failed.")
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

