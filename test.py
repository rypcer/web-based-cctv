def func():
	
	for i in range(5):
		print("X")
		yield i
g = func()
print(next(g))
print(next(g))
print(next(g))

