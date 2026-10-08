# Diagrams

One [d2](https://d2lang.com) diagram for the start (`-before`) and the solution (`-after`) of each exercise, plus
`12-final` for the complete taxi company. `style.d2` holds the shared style, and `./build.sh` renders every `.d2`
file to `.svg`.

 * Oval: a service. Hexagon: an exchange. Cylinder: a queue. Folded page: a policy
 * Solid arrow: publish or consume. Dashed orange arrow: routing inside the broker (bindings, alternate exchange,
   dead-lettering). Dotted arrow: a policy applying to a queue or exchange
 * Faded and dashed: missing, not declared yet, or lost
 * Orange outline: added or changed by the exercise (only in the `-after` diagrams)

From exercise 06 on, each diagram leaves out the parts the exercise doesn't touch. The note under the diagram says
which ones.
