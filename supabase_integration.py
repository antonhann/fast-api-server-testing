from enum import Enum
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException, Path, Query
import os
from supabase import create_client, Client

app = FastAPI()

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

class Category(Enum):
    TOOLS = "tools"
    CONSUMABLES = "consumables"


class Item(BaseModel):
    name: str
    price: float
    count: int
    category: Category


items = {
    0: Item(name="Hammer", price=9.99, count=20, id=0, category=Category.TOOLS),
    1: Item(name="Pliers", price=5.99, count=20, id=1, category=Category.TOOLS),
    2: Item(name="Nails", price=1.99, count=100, id=2, category=Category.CONSUMABLES),
}
        
@app.get("/")
def index() -> dict[str, list[Item]]:
    response = supabase.table("items").select("*").execute()
    items = [Item(**item) for item in response.data]
    return {"data": items}

Selection = dict[
    str, str | int | float | Category | None
]  # dictionary containing the user's query arguments


@app.get("/items/")
def query_item_by_parameters(
    name: str | None = None,
    price: float | None = None,
    count: int | None = None,
    category: Category | None = None,
)-> dict[str, Selection|list[Item]]:
    query = supabase.table("items").select("*")

    if name is not None:
        query = query.eq("name", name)
    
    if price is not None:
        query = query.eq("price", price)
    
    if count is not None:
        query = query.eq("count", count)
    
    if category is not None:
        query = query.eq("category", category.value)  # Use .value to get the string representation of the Enum
        # Convert the raw data to a list of Item instances
    response = query.execute()
    items = [Item(**item) for item in response.data]  # Unpack the data into Item models

    return {
        "query": {"name": name, "price": price, "count": count, "category": category},
        "selection": items,  # Return the validated list of Item models
    }


@app.post("/")
def add_item(item: Item) -> dict[str, Item]:
    data = item.model_dump()
    data["category"] = item.category.value
    response = supabase.table("items").insert(data).execute()
    print(response)
    return {"added": item}



# We can place further restrictions on allowed arguments by using the Query and Path classes.
# In this case we are setting a lower bound for valid values and a minimal and maximal length for the name.
@app.put("/update/{item_id}")
def update(
    item_id: int = Path(ge=0),
    name: str | None = Query(default=None, min_length=1, max_length=8),
    price: float | None = Query(default=None, gt=0.0),
    count: int | None = Query(default=None, ge=0),
    category: Category | None = Query(default=None)
):
    existing_item_response = supabase.table("items").select("*").eq("id", item_id).execute()
    print(name, price, count, category)
    # Check if the item exists
    if not existing_item_response.data:
        return {"message": "Item not found"}, 404

    existing_item = existing_item_response.data[0]
    update_data = {}
    
    # Prepare data for updating only the provided fields
    if name is not None:
        update_data["name"] = name
    if price is not None:
        update_data["price"] = price
    if count is not None:
        update_data["count"] = count
    if category is not None:
        update_data["category"] = category.value  # Assuming category is an Enum with a value attribute

    # Update in the database only if there are fields to update
    if update_data:
        response = supabase.table("items").update(update_data).eq("id", item_id).execute()
        if not response.data:
            return {"message": "Item was not updated", "data": response.data}, 400
        else:
            return {"message": "Item updated successfully", "data": response.data}, 200
    else:
        return {"message": "No fields to update"}, 400


@app.delete("/delete/{item_id}")
def delete_item(item_id: int) -> dict[str, Item]:
    response = supabase.table("items").delete().eq("id",item_id).execute()
    deleted = []
    if response.data:
        deleted = response.data[0]
    return {"deleted": deleted}

# To run the server, use the following command: uvicorn supabase_integration:app --reload
"""
to grant access to the table, run the following SQL commands: (when creating a table)
-- Enable Row-Level Security for table_name
ALTER TABLE public.table_name ENABLE ROW LEVEL SECURITY;


--SELECTSELECTSELECTSELECTSELECTSELECTSELECTSELECTSELECT
-- Allow authenticated users to SELECT from table_name
CREATE POLICY "Allow authenticated users to select" 
ON public.table_name
FOR SELECT
USING (auth.uid() IS NOT NULL);

--INSERTINSERTINSERTINSERTINSERTINSERTINSERTINSERTINSERT
-- Allow authenticated users to INSERT into table_name
CREATE POLICY "Allow authenticated users to insert" 
ON public.table_name
FOR INSERT
WITH CHECK (auth.uid() IS NOT NULL);

--UPDATEUPDATEUPDATEUPDATEUPDATEUPDATEUPDATEUPDATEUPDATEUPDATE
-- Allow authenticated users to UPDATE records in table_name
CREATE POLICY "Allow authenticated users to update" 
ON public.table_name
FOR UPDATE
USING (auth.uid() IS NOT NULL);

--DELETEDELETEDELETEDELETEDELETEDELETEDELETEDELETEDELETEDELETEDELETE
-- Allow authenticated users to DELETE from table_name
CREATE POLICY "Allow authenticated users to delete" 
ON public.table_name
FOR DELETE
USING (auth.uid() IS NOT NULL);

--After creating the policy, you may need to enable RLS for the table if it’s not already enabled:
ALTER TABLE items ENABLE ROW LEVEL SECURITY;
"""