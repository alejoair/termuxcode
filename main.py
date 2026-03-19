def calculate(p, t, d):
    if p == "S":
        price = 10
    else:
        if p == "M":
            price = 15
        else:
            if p == "L":
                price = 20
    
    if t > 0:
        price = price + (t * 1.5)
        
    if d > 5:
        price = price + 5
    else:
        price = price + 2
        
    return price