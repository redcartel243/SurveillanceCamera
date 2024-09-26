def solution(A, X, Y):
    if not A or len(A) < 1:
        return 0

    A.sort()
    r = float('inf')
    left = 0
    right = 0
    i = 0
    j = 0

    while True:
        while j < len(A) - i and (left + A[j]) <= right:
            left += A[j]
            j += 1
        
        r = min(r, X * max(len(A) - j - i, 0) + Y * i)
        
        i += 1
        if i > len(A):
            break

        right += A[len(A) - i]

    return r

# Example usage:
print(solution([5, 3, 8, 3, 2], 2, 5))   # Output: 7
print(solution([4, 2, 7], 4, 100))       # Output: 12
print(solution([2, 2, 1, 2, 2], 2, 3))   # Output: 8
print(solution([4, 1, 5, 3], 5, 2))      # Output: 4