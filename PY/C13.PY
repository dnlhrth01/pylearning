# Parent class
class Shape:
    def __init__(self, name):
        self.name = name

    def area(self):
        return 0


class Circle(Shape):
    def __init__(self, radius):
        super().__init__("Circle")
        self.radius = radius

    def area(self):
        return 3.14 * float(self.radius * self.radius)


class Square(Shape):
    def __init__(self, side):
        super().__init__("Square")
        self.side = side

    def area(self):
        return float(self.side * self.side)


circle = Circle(5)
square = Square(4)

# Polymorphism
def print_area(shape): # Takes any Shape
    print(f"{shape.name} area: {shape.area():.2f}")

# Same method call, different behaviors
# "Circle area: 78.5"
# "Square area: 16"

print_area(circle)
print_area(square)

# Or with a list
shapes = [Circle(3), Square(5), Circle(2)]
for shape in shapes:
    print_area(shape) # Same code, different results