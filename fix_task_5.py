from main import engine, Task, Phase, Todo, Session, update_todos_when_phase_completed, recalculate_task_progress

def fix_task_5():
    with Session(engine) as session:
        task = session.get(Task, 5)
        if not task:
            print("Task 5 not found")
            return

        print(f"Task 5 loaded: {task.name}, Status: {task.status}")
        
        # Manually complete all phases
        for phase in task.phases:
            print(f"Completing phase: {phase.name}")
            phase.status = "completed"
            session.add(phase)
            # Commit phase update first to ensure ID is valid for the helper
            session.commit()
            
            # Helper re-fetches phase, so this is safe
            update_todos_when_phase_completed(phase.id, session)
        
        session.commit()
        
        # Now recalculate
        recalculate_task_progress(5, session)
        session.refresh(task)
        print(f"Task 5 final status: {task.status}, Progress: {task.progress_percent}")

if __name__ == "__main__":
    fix_task_5()